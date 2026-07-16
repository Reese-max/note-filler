#!/usr/bin/env python
"""
Dependency Upgrade Verification Script

此腳本用於驗證最新相容版本的 fastapi、starlette、httpx 是否通過完整測試套件。
它會在隔離的臨時 venv 中安裝依賴並執行測試，確保升級後不會破壞現有功能。

使用方式:
    python scripts/dep_upgrade_check.py

或使用指定的 Python:
    python -X utf8 scripts/dep_upgrade_check.py
"""

import subprocess
import sys
import tempfile
import shutil
import os
from pathlib import Path


def run_command(cmd, cwd=None, check=True, capture_output=True):
    """執行命令並返回結果"""
    print(f"執行: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def main():
    """主函數"""
    script_dir = Path(__file__).parent.parent
    constraints_file = script_dir / "constraints-pinned.txt"
    
    if not constraints_file.exists():
        print(f"錯誤: 找不到 constraints 檔案: {constraints_file}")
        sys.exit(1)
    
    print(f"使用 constraints 檔案: {constraints_file}")
    print(f"專案根目錄: {script_dir}")
    
    # 建立臨時 venv 目錄
    temp_dir = tempfile.mkdtemp(prefix="dep_upgrade_check_")
    venv_dir = Path(temp_dir) / "venv"
    
    try:
        print(f"\n建立臨時 venv: {venv_dir}")
        run_command([sys.executable, "-m", "venv", str(venv_dir)])
        
        # 確定 venv 中的 Python 和 pip
        if os.name == 'nt':  # Windows
            venv_python = venv_dir / "Scripts" / "python.exe"
            venv_pip = venv_dir / "Scripts" / "pip.exe"
        else:  # Unix-like
            venv_python = venv_dir / "bin" / "python"
            venv_pip = venv_dir / "bin" / "pip"
        
        if not venv_python.exists():
            print(f"錯誤: venv Python 不存在: {venv_python}")
            sys.exit(1)
        
        print(f"升級 pip")
        run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
        
        print(f"\n安裝專案依賴（使用 constraints-pinned.txt）")
        run_command([
            str(venv_pip),
            "install",
            "-e",
            str(script_dir),
            "-e",
            f"{script_dir}[dev]",
            "-c",
            str(constraints_file)
        ])
        
        print(f"\n驗證安裝的版本")
        run_command([
            str(venv_python),
            "-m",
            "pip",
            "show",
            "fastapi",
            "starlette",
            "httpx"
        ])
        
        print(f"\n執行測試套件（跳過 integration 測試）")
        test_result = run_command([
            str(venv_python),
            "-m",
            "pytest",
            "tests/",
            "-m",
            "not integration",
            "-v"
        ], cwd=script_dir, check=False)
        
        if test_result.returncode == 0:
            print("\n✅ 所有測試通過！")
            return 0
        else:
            print("\n❌ 測試失敗")
            return 1
            
    finally:
        print(f"\n清理臨時 venv: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())