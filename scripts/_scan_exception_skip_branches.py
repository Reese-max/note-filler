"""Scan note_filler src/app for except / continue / empty-return / raise branches.

Evidence producer for exception-skip inventory. Pure stdlib; no deps.
"""
from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "note_filler"
APP = ROOT / "app"
OUT = ROOT / "docs" / "evidence" / "exception-skip-branch-scan-2026-07-24.json"
TEXT_OUT = ROOT / "docs" / "evidence" / "exception-skip-branch-scan-2026-07-24.txt"


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path, source_lines: list[str]) -> None:
        self.path = path
        self.lines = source_lines
        self.stack: list[ast.AST] = []
        self.results: list[dict] = []

    def _fn(self) -> str:
        for n in reversed(self.stack):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return n.name
        return "<module>"

    def _line(self, node: ast.AST) -> str:
        if hasattr(node, "lineno") and 1 <= node.lineno <= len(self.lines):
            return self.lines[node.lineno - 1].rstrip()
        return ""

    def generic_visit(self, node: ast.AST) -> None:
        self.stack.append(node)
        super().generic_visit(node)
        self.stack.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            typ = "bare"
        elif isinstance(node.type, ast.Name):
            typ = node.type.id
        elif isinstance(node.type, ast.Tuple):
            parts = []
            for elt in node.type.elts:
                parts.append(elt.id if isinstance(elt, ast.Name) else ast.dump(elt))
            typ = "|".join(parts)
        else:
            typ = ast.dump(node.type)

        has_raise = any(isinstance(s, ast.Raise) for s in node.body)
        has_return = any(isinstance(s, ast.Return) for s in node.body)
        has_continue = any(isinstance(s, ast.Continue) for s in node.body)
        has_pass = any(isinstance(s, ast.Pass) for s in node.body)

        logs: list[str] = []
        for s in ast.walk(node):
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute):
                if s.func.attr in ("warning", "error", "exception", "info", "debug"):
                    if isinstance(s.func.value, ast.Name) and s.func.value.id in (
                        "logger",
                        "logging",
                    ):
                        logs.append(f"logger.{s.func.attr}")
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Name):
                if s.func.id == "audit_event":
                    logs.append("audit_event")
                if s.func.id == "print":
                    logs.append("print")

        self.results.append(
            {
                "kind": "except",
                "file": str(self.path.relative_to(ROOT)).replace("\\", "/"),
                "line": node.lineno,
                "function": self._fn(),
                "exc_type": typ,
                "has_raise": has_raise,
                "has_return": has_return,
                "has_continue": has_continue,
                "has_pass": has_pass,
                "logs": logs,
                "source": self._line(node),
            }
        )
        self.generic_visit(node)

    def visit_Continue(self, node: ast.Continue) -> None:
        self.results.append(
            {
                "kind": "continue",
                "file": str(self.path.relative_to(ROOT)).replace("\\", "/"),
                "line": node.lineno,
                "function": self._fn(),
                "source": self._line(node),
            }
        )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        src = self._line(node)
        interesting = False
        if node.value is None:
            interesting = True
        elif isinstance(node.value, (ast.List, ast.Dict, ast.Tuple)) and not getattr(
            node.value, "elts", True
        ):
            interesting = True
        elif isinstance(node.value, (ast.List, ast.Dict, ast.Tuple)):
            if isinstance(node.value, ast.Dict):
                interesting = not node.value.keys
            else:
                interesting = not node.value.elts
        elif isinstance(node.value, ast.Constant) and node.value.value in (
            None,
            "",
            0,
            False,
        ):
            interesting = True
        elif isinstance(node.value, ast.NameConstant):  # py3.7 compat unused
            interesting = True
        if interesting or any(
            token in src
            for token in (
                "return []",
                "return None",
                "return {}",
                'return ""',
                "return ''",
            )
        ):
            self.results.append(
                {
                    "kind": "return_emptyish",
                    "file": str(self.path.relative_to(ROOT)).replace("\\", "/"),
                    "line": node.lineno,
                    "function": self._fn(),
                    "source": src,
                }
            )
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        self.results.append(
            {
                "kind": "raise",
                "file": str(self.path.relative_to(ROOT)).replace("\\", "/"),
                "line": node.lineno,
                "function": self._fn(),
                "source": self._line(node),
            }
        )
        self.generic_visit(node)


def main() -> int:
    all_results: list[dict] = []
    for base in (SRC, APP):
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.py")):
            text = p.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(p))
            v = Visitor(p, text.splitlines())
            v.visit(tree)
            all_results.extend(v.results)

    counts = Counter(r["kind"] for r in all_results)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("KIND_COUNTS", dict(counts))
    print("TOTAL", len(all_results))
    print("WROTE", OUT)
    lines = [f"KIND_COUNTS {dict(counts)}", f"TOTAL {len(all_results)}"]
    for r in all_results:
        if r["kind"] == "except":
            line = (
                f"except|{r['file']}:{r['line']}|{r['function']}|"
                f"exc={r['exc_type']}|logs={r['logs']}|"
                f"ret={r['has_return']}|cont={r['has_continue']}|raise={r['has_raise']}|"
                f"{r['source'][:120]}"
            )
        else:
            line = f"{r['kind']}|{r['file']}:{r['line']}|{r['function']}|{r['source'][:120]}"
        lines.append(line)
        print(line)
    TEXT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("WROTE", TEXT_OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
