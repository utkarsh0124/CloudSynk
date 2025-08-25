#!/usr/bin/env bash
set -euo pipefail

# Modular test runner for the project.
# Usage:
#   ./scripts/run_all_tests.sh            # run both backend and frontend
#   ./scripts/run_all_tests.sh backend    # run only backend (Django)
#   ./scripts/run_all_tests.sh frontend   # run only frontend (Jest)
# Additional args are passed to the underlying test runner (manage.py test args for backend).

ROOT_DIR=""
if [ -n "${BASE_DIR:-}" ]; then
    ROOT_DIR="${BASE_DIR}"
else
    echo "ERROR: BASE_DIR not set. Aborting!"
    exit 1
fi
echo "BASE_DIR : ${BASE_DIR}"
cd "$ROOT_DIR"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
banner() { printf "\n==== %s - %s ====\n" "$(timestamp)" "$1"; }

# Prepare reports directory and report file
REPORT_DIR="$ROOT_DIR/scripts/reports"
mkdir -p "$REPORT_DIR"
REPORT_TS=$(date -u +"%Y%m%dT%H%M%SZ")
REPORT_FILE_JSON="$REPORT_DIR/test_report_${REPORT_TS}.json"

write_report() {
    # Arguments: backend_out, backend_rc, frontend_out, frontend_rc
    local backend_out="$1" backend_rc="$2" frontend_out="$3" frontend_rc="$4"

    # Backend metrics
    local backend_total=0 backend_time=0 backend_status="unknown"
    local backend_tests_json="[]"
    # If the backend_out file doesn't include the test summary, try to find a recent file
    # in the reports dir that does (fallback for cases where output landed elsewhere).
    if [ -f "$backend_out" ]; then
        if ! tr -d '\r' < "$backend_out" | grep -E "^Ran [0-9]+ tests? in" -q 2>/dev/null; then
            # find most recent file in REPORT_DIR that contains the Ran line
            candidate=$(grep -El "Ran [0-9]+ tests? in" "$REPORT_DIR"/* 2>/dev/null | tail -n1 || true)
            if [ -n "$candidate" ]; then
                backend_out="$candidate"
            fi
        fi
    fi
    if [ -f "$backend_out" ]; then
        # Extract Ran line: "Ran 9 tests in 3.631s"
        local ran_line
        # strip CRs to be robust against different EOLs
        ran_line=$(tr -d '\r' < "$backend_out" | grep -E "^Ran [0-9]+ tests? in" | tail -n1 || true)
        if [ -n "$ran_line" ]; then
            # example: Ran 13 tests in 3.503s
            backend_total=$(echo "$ran_line" | awk '{print $2}')
            # extract time value (number before 's') robustly
            backend_time=$(echo "$ran_line" | sed -E 's/.* in ([0-9.]+)s/\1/')
        fi
        if [ "$backend_rc" -eq 0 ]; then backend_status="OK"; else backend_status="FAILED"; fi

        # Extract per-test lines like: test_name (module.Class) ... ok
        # Strip CRs first, relax end anchor to be robust
    mapfile -t _b_lines < <(tr -d '\r' < "$backend_out" | grep -E ' \.\.\. (ok|FAIL)' || true)
        local _arr_b=()
        for l in "${_b_lines[@]}"; do
            # status is the trailing ok or FAIL
            local status=$(echo "$l" | sed -E 's/.* \.\.\. (ok|FAIL)/\1/')
            # name is the line without the trailing status marker
            local name=$(echo "$l" | sed -E 's/ \.\.\. (ok|FAIL)//')
            name=$(echo "$name" | sed 's/"/\\"/g')
            _arr_b+=("{\"name\":\"$name\",\"status\":\"$status\"}")
        done
        if [ ${#_arr_b[@]} -gt 0 ]; then
            backend_tests_json="[$(IFS=,; echo "${_arr_b[*]}")]"
        fi
    fi

    # Frontend metrics
    local frontend_suites=0 frontend_tests=0 frontend_time=0 frontend_status="unknown"
    local frontend_suites_json="[]"
    if [ -f "$frontend_out" ]; then
        # Extract summary lines
        local suites_line tests_line time_line
        suites_line=$(grep -E "^Test Suites:" "$frontend_out" | tail -n1 || true)
        tests_line=$(grep -E "^Tests:" "$frontend_out" | tail -n1 || true)
        time_line=$(grep -E "^Time:" "$frontend_out" | tail -n1 || true)
        if [ -n "$suites_line" ]; then
            # e.g. Test Suites: 2 passed, 2 total
            frontend_suites=$(echo "$suites_line" | sed -E 's/.*: *([0-9]+).*/\1/')
        fi
        if [ -n "$tests_line" ]; then
            frontend_tests=$(echo "$tests_line" | sed -E 's/.*: *([0-9]+).*/\1/')
        fi
        if [ -n "$time_line" ]; then
            frontend_time=$(echo "$time_line" | sed -E 's/Time: *([0-9.]+) s/\1/')
        fi
        if [ "$frontend_rc" -eq 0 ]; then frontend_status="OK"; else frontend_status="FAILED"; fi

        # Extract PASS/FAIL suite lines
        mapfile -t _f_lines < <(grep -E '^(PASS|FAIL) ' "$frontend_out" || true)
        local _arr_f=()
        for l in "${_f_lines[@]}"; do
            local status=$(echo "$l" | awk '{print $1}')
            local name=$(echo "$l" | sed -E 's/^(PASS|FAIL) //')
            name=$(echo "$name" | sed 's/"/\\\"/g')
            _arr_f+=("{\"name\":\"$name\",\"status\":\"$status\"}")
        done
        if [ ${#_arr_f[@]} -gt 0 ]; then
            frontend_suites_json="[$(IFS=,; echo "${_arr_f[*]}")]"
        fi
    fi

    # Build JSON
    cat > "$REPORT_FILE_JSON" <<EOF
{
  "timestamp": "${REPORT_TS}",
  "generated_at": "$(timestamp)",
  "backend": {
    "status": "${backend_status}",
    "total_tests": ${backend_total},
    "time_seconds": ${backend_time},
    "tests": ${backend_tests_json}
  },
  "frontend": {
    "status": "${frontend_status}",
    "suites": ${frontend_suites},
    "tests": ${frontend_tests},
    "time_seconds": ${frontend_time},
    "suites_list": ${frontend_suites_json}
  }
}
EOF

    echo "Report written to: $REPORT_FILE_JSON"

    # Keep only 1 most recent JSON reports
    ls -1t "$REPORT_DIR"/test_report_*.json 2>/dev/null | sed -n '2,$p' | xargs -r rm -f
}

run_backend() {
    banner "BACKEND TESTS (Django) START"
    echo "[backend] enabling API endpoints for this run"
    export ENABLE_API_ENDPOINTS=true
    # Use verbosity 2 to list each test that runs for clearer output
    # Create temp files inside the reports directory so write_report can always read them
    backend_tmp=$(mktemp "$REPORT_DIR/backend_out.XXXXXX")
    if [ ${#BACKEND_ARGS[@]} -gt 0 ]; then
        # Capture both stdout and stderr so per-test lines are saved
        ./manage.py test -v2 "${BACKEND_ARGS[@]}" 2>&1 | tee "$backend_tmp"
        rc=${PIPESTATUS[0]}
    else
        # Run only the API tests package by default to avoid discovery/import issues
        # Capture both stdout and stderr so per-test lines are saved
        ./manage.py test -v2 main.api_tests 2>&1 | tee "$backend_tmp"
        rc=${PIPESTATUS[0]}
    fi
    if [ $rc -ne 0 ]; then
        echo "[backend] Django tests failed (exit $rc)"
        unset ENABLE_API_ENDPOINTS
        BACKEND_OUT="$backend_tmp"
        BACKEND_RC=$rc
        return $rc
    fi
    echo "[backend] Django tests completed OK"
    unset ENABLE_API_ENDPOINTS
    banner "BACKEND TESTS (Django) END"
    BACKEND_OUT="$backend_tmp"
    BACKEND_RC=$rc
    return 0
}

run_frontend() {
    banner "FRONTEND TESTS (Jest) START"
    # Create frontend temp file inside reports directory so write_report can read it
    frontend_tmp=$(mktemp "$REPORT_DIR/frontend_out.XXXXXX")
    npm test --silent 2>&1 | tee "$frontend_tmp"
    rc=${PIPESTATUS[0]}
    if [ $rc -ne 0 ]; then
        echo "[frontend] Jest tests failed (exit $rc)"
        FRONTEND_OUT="$frontend_tmp"
        FRONTEND_RC=$rc
        return $rc
    fi
    echo "[frontend] Jest tests completed OK"
    banner "FRONTEND TESTS (Jest) END"
    FRONTEND_OUT="$frontend_tmp"
    FRONTEND_RC=$rc
    return 0
}

help() {
    cat <<'USAGE'
Usage: run_all_tests.sh [all|backend|frontend] [-- <backend args>]

Examples:
  ./scripts/run_all_tests.sh                # run backend then frontend
  ./scripts/run_all_tests.sh backend -- -k test_specific
  ./scripts/run_all_tests.sh frontend       # run only frontend tests
USAGE
}

# Parse subcommand
SUBCOMMAND="all"
BACKEND_ARGS=()
if [ $# -ge 1 ]; then
    case "$1" in
        all|backend|frontend)
            SUBCOMMAND="$1"; shift
            ;;
        -h|--help)
            help; exit 0
            ;;
        --)
            SUBCOMMAND="all"; shift
            ;;
        *)
            # If first arg starts with dash, treat as backend args
            if [[ "$1" == -* ]]; then
                SUBCOMMAND="all"
            else
                echo "Unknown subcommand: $1"; help; exit 2
            fi
            ;;
    esac
fi

# Collect backend args after -- separator or all remaining args
if [ $# -gt 0 ]; then
    if [ "$1" = "--" ]; then
        shift
        BACKEND_ARGS=("$@")
    else
        BACKEND_ARGS=("$@")
    fi
fi

case "$SUBCOMMAND" in
    backend)
        run_backend
        exit $?
        ;;
    frontend)
        run_frontend
        exit $?
        ;;
    all)
    run_backend || true
    run_frontend || true
    # Generate a report file summarizing outputs
    write_report "${BACKEND_OUT:-}" "${BACKEND_RC:-}" "${FRONTEND_OUT:-}" "${FRONTEND_RC:-}"
    # Validate generated JSON report meets thresholds and statuses
    check_report() {
        local report_file="$REPORT_FILE_JSON"
        local be_expect=${BACKEND_EXPECT:-13}
        local fe_expect=${FRONTEND_EXPECT:-10}
        local failed=0

        if [ ! -f "$report_file" ]; then
            echo "[report-check] FAIL: report file not found: $report_file"
            return 2
        fi

        if command -v jq >/dev/null 2>&1; then
            backend_total=$(jq -r '.backend.total_tests // 0' "$report_file")
            frontend_total=$(jq -r '.frontend.tests // 0' "$report_file")
            # find any backend test whose status != ok
            non_ok_backend=$(jq -r '.backend.tests[]? | select(.status != "ok") | "\(.name):\(.status)"' "$report_file" | head -n1 || true)
            # find any frontend suite whose status != PASS
            non_pass_frontend=$(jq -r '.frontend.suites_list[]? | select(.status != "PASS") | "\(.name):\(.status)"' "$report_file" | head -n1 || true)
            backend_status=$(jq -r '.backend.status // ""' "$report_file")
            frontend_status=$(jq -r '.frontend.status // ""' "$report_file")
        else
            # fallback using grep/sed for environments without jq
            backend_total=$(grep -oE '"total_tests"[[:space:]]*:[[:space:]]*[0-9]+' "$report_file" | tail -n1 | sed -E 's/.*: *([0-9]+)$/\1/' || echo 0)
            frontend_total=$(grep -oE '"tests"[[:space:]]*:[[:space:]]*[0-9]+' "$report_file" | head -n1 | sed -E 's/.*: *([0-9]+)$/\1/' || echo 0)
            # backend tests non-ok detection
            non_ok_backend=$(grep -o '{[^}]*"status"[^}]*}' "$report_file" | sed -E 's/.*"status"\s*:\s*"?([^",}]*)"?.*/\1/' | nl -ba | while read -r n s; do if [ "$(echo "$s" | tr '[:upper:]' '[:lower:]')" != "ok" ]; then echo "non-ok"; break; fi; done || true)
            non_pass_frontend=$(grep -o '{[^}]*"status"[^}]*}' "$report_file" | sed -E 's/.*"status"\s*:\s*"?([^",}]*)"?.*/\1/' | nl -ba | while read -r n s; do if [ "$(echo "$s" | tr '[:lower:]' '[:upper:]')" != "PASS" ]; then echo "non-pass"; break; fi; done || true)
            backend_status=$(grep -E '"backend"[[:space:]]*:\s*\{' -n -n "$report_file" >/dev/null 2>&1 && grep -A3 '"backend"' "$report_file" | grep -oE '"status"\s*:\s*"[^"]+"' | head -n1 | sed -E 's/.*: *"([^"]+)"/\1/' || echo "")
            frontend_status=$(grep -A3 '"frontend"' "$report_file" | grep -oE '"status"\s*:\s*"[^"]+"' | head -n1 | sed -E 's/.*: *"([^"]+)"/\1/' || echo "")
        fi

        # [1] compare totals
        if [ "$backend_total" -lt "$be_expect" ]; then
            echo "[report-check] FAIL: backend total tests ($backend_total) < expected ($be_expect)"
            failed=1
        else
            echo "[report-check] backend total tests: $backend_total (>= $be_expect)"
        fi

        if [ "$frontend_total" -lt "$fe_expect" ]; then
            echo "[report-check] FAIL: frontend total tests ($frontend_total) < expected ($fe_expect)"
            failed=1
        else
            echo "[report-check] frontend total tests: $frontend_total (>= $fe_expect)"
        fi

        # [2] ensure backend tests all ok and frontend suites PASS
        if [ -n "$non_ok_backend" ]; then
            echo "[report-check] FAIL: found backend tests with non-ok status: $non_ok_backend"
            failed=1
        else
            echo "[report-check] all backend tests have status ok"
        fi

        if [ -n "$non_pass_frontend" ]; then
            echo "[report-check] FAIL: found frontend suites not PASS: $non_pass_frontend"
            failed=1
        else
            echo "[report-check] all frontend suites have status PASS"
        fi

        # [3] overall statuses
        if [ "${backend_status:-}" != "OK" ]; then
            echo "[report-check] FAIL: backend overall status is not OK: ${backend_status:-}"; failed=1
        else
            echo "[report-check] backend overall status OK"
        fi
        if [ "${frontend_status:-}" != "OK" ]; then
            echo "[report-check] FAIL: frontend overall status is not OK: ${frontend_status:-}"; failed=1
        else
            echo "[report-check] frontend overall status OK"
        fi

        if [ "$failed" -eq 0 ]; then
            echo "[report-check] SUCCESS: report meets all checks"
            return 0
        else
            echo "[report-check] FAIL: one or more checks failed"
            return 4
        fi
    }

    check_report || exit $?
    # Propagate non-zero exit codes if any
    if [ "${BACKEND_RC:-0}" -ne 0 ]; then exit ${BACKEND_RC}; fi
    if [ "${FRONTEND_RC:-0}" -ne 0 ]; then exit ${FRONTEND_RC}; fi
    echo "[run_all_tests] All tests passed."
    exit 0
        ;;
    *)
        help; exit 2
        ;;
esac

