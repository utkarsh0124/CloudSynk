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
    if [ -f "$backend_out" ]; then
        # Extract Ran line: "Ran 9 tests in 3.631s"
        local ran_line
        ran_line=$(grep -E "^Ran [0-9]+ tests? in" "$backend_out" | tail -n1 || true)
        if [ -n "$ran_line" ]; then
            backend_total=$(echo "$ran_line" | awk '{print $2}')
            backend_time=$(echo "$ran_line" | awk '{print $5}' | sed 's/s$//')
        fi
        if [ "$backend_rc" -eq 0 ]; then backend_status="OK"; else backend_status="FAILED"; fi

        # Extract per-test lines like: test_name (module.Class) ... ok
        mapfile -t _b_lines < <(grep -E ' \.\.\. (ok|FAIL)$' "$backend_out" || true)
        local _arr_b=()
        for l in "${_b_lines[@]}"; do
            local status=$(echo "$l" | sed -E 's/.* \.\.\. (ok|FAIL)$/\1/')
            local name=$(echo "$l" | sed -E 's/ \.\.\. (ok|FAIL)$//')
            name=$(echo "$name" | sed 's/"/\\\"/g')
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
    backend_tmp=$(mktemp)
    if [ ${#BACKEND_ARGS[@]} -gt 0 ]; then
        ./manage.py test -v2 "${BACKEND_ARGS[@]}" | tee "$backend_tmp"
        rc=${PIPESTATUS[0]}
    else
        ./manage.py test -v2 | tee "$backend_tmp"
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
    frontend_tmp=$(mktemp)
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

