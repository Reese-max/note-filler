#!/usr/bin/env bash
# run_tests.sh -- Run tests with clear integration/non-integration separation
# Usage:
#   ./scripts/run_tests.sh          # non-integration only (CI default)
#   ./scripts/run_tests.sh all      # full suite (unit + integration)
#   ./scripts/run_tests.sh unit     # same as default
#   ./scripts/run_tests.sh integ    # integration tests only
#   ./scripts/run_tests.sh check    # list collected tests without running
#
# Environment:
#   PYTEST_EXTRA   extra pytest args, e.g. PYTEST_EXTRA="-k test_domain" ./scripts/run_tests.sh
#   PYTHON         python binary override, default: python

set -euo pipefail

PYTHON="${PYTHON:-python}"
PYTEST_ARGS=("${PYTEST_EXTRA:-}")

usage() {
    echo "Usage: $0 [unit|all|integ|check]"
    echo ""
    echo "  (no args)  Run non-integration tests (CI default)"
    echo "  unit       Same as above"
    echo "  all        Full suite: non-integration + integration"
    echo "  integ      Integration tests only (requires grok proxy on :8318)"
    echo "  check      Collect and list tests without running"
    exit 1
}

MODE="${1:-unit}"

case "$MODE" in
    unit|"")
        echo "=== Running non-integration tests (default CI mode) ==="
        echo "    Skipping: @pytest.mark.integration (8 tests)"
        echo ""
        $PYTHON -m pytest tests/ \
            -m "not integration" \
            -v \
            "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}"
        ;;
    all)
        echo "=== Running FULL test suite (unit + integration) ==="
        echo "    Integration tests require: grok proxy on 127.0.0.1:8318"
        echo "    Tests will be skipped (not failed) if grok is unreachable."
        echo ""
        $PYTHON -m pytest tests/ \
            -m "" \
            -v \
            "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}"
        ;;
    integ|integration)
        echo "=== Running integration tests ONLY ==="
        echo "    Requires: grok proxy on 127.0.0.1:8318"
        echo "    Tests will be skipped (not failed) if grok is unreachable."
        echo ""
        $PYTHON -m pytest tests/ \
            -m "integration" \
            -v \
            "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}"
        ;;
    check|collect)
        echo "=== Collecting tests (no execution) ==="
        echo ""
        echo "--- Non-integration tests ---"
        $PYTHON -m pytest tests/ -m "not integration" --co -q 2>/dev/null || true
        echo ""
        echo "--- Integration tests ---"
        $PYTHON -m pytest tests/ -m "integration" --co -q 2>/dev/null || true
        ;;
    -h|--help)
        usage
        ;;
    *)
        echo "ERROR: Unknown mode '$MODE'"
        usage
        ;;
esac
