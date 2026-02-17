#!/usr/bin/env bash
# Nereus Platform Launcher
# Usage:
#   ./launch.sh v4          # Dashboard v4 (port 8504) + API
#   ./launch.sh v3          # Dashboard v3 (port 8503) + API
#   ./launch.sh v2          # Dashboard v2 (port 8501) + API
#   ./launch.sh v1          # Dashboard v1 (port 8500) - static, no API
#   ./launch.sh api         # API server only
#   ./launch.sh stop        # Stop all running services

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
DEMO_DIR="$SCRIPT_DIR/investor_demo"
PID_DIR="$SCRIPT_DIR/.pids"

# Port assignments
API_PORT=8000
ALL_DASH_PORTS="8500 8501 8503 8504"

get_port() {
    case "$1" in
        v1) echo 8500 ;;
        v2) echo 8501 ;;
        v3) echo 8503 ;;
        v4) echo 8504 ;;
    esac
}

get_file() {
    case "$1" in
        v1) echo "streamlit_app.py" ;;
        v2) echo "streamlit_app_v2.py" ;;
        v3) echo "streamlit_app_v3.py" ;;
        v4) echo "streamlit_app_v4.py" ;;
    esac
}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

mkdir -p "$PID_DIR"

# ---- helpers ----

log()  { echo -e "${GREEN}[nereus]${NC} $1"; }
warn() { echo -e "${YELLOW}[nereus]${NC} $1"; }
err()  { echo -e "${RED}[nereus]${NC} $1" >&2; }

load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$ENV_FILE"
        set +a
    else
        err ".env not found at $ENV_FILE"
        exit 1
    fi
}

check_neo4j() {
    python3 -c "
from neo4j import GraphDatabase
try:
    d = GraphDatabase.driver('${MARIS_NEO4J_URI:-bolt://localhost:7687}', auth=('neo4j', '${MARIS_NEO4J_PASSWORD:-}'))
    d.verify_connectivity()
    d.close()
    print('ok')
except Exception as e:
    print(f'fail:{e}')
" 2>/dev/null
}

wait_for_api() {
    local retries=15
    while (( retries > 0 )); do
        if curl -s "http://localhost:$API_PORT/api/health" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
        (( retries-- )) || true
    done
    return 1
}

stop_service() {
    local name="$1"
    local pidfile="$PID_DIR/${name}.pid"
    if [[ -f "$pidfile" ]]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
            log "Stopped $name (PID $pid)"
        fi
        rm -f "$pidfile"
    fi
}

stop_all() {
    log "Stopping all Nereus services..."
    stop_service "api"
    stop_service "dashboard"
    # Also kill by port as fallback
    lsof -ti ":$API_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
    for port in $ALL_DASH_PORTS; do
        lsof -ti ":$port" 2>/dev/null | xargs kill 2>/dev/null || true
    done
    log "All services stopped."
}

start_api() {
    log "Starting API server on port $API_PORT..."
    cd "$SCRIPT_DIR"
    uvicorn maris.api.main:app --host 0.0.0.0 --port "$API_PORT" \
        > "$PID_DIR/api.log" 2>&1 &
    echo $! > "$PID_DIR/api.pid"

    if wait_for_api; then
        log "API server ready at ${CYAN}http://localhost:$API_PORT${NC}"
    else
        err "API server failed to start. Check $PID_DIR/api.log"
        cat "$PID_DIR/api.log"
        exit 1
    fi
}

start_dashboard() {
    local version="$1"
    local port
    local file
    port=$(get_port "$version")
    file=$(get_file "$version")

    if [[ ! -f "$DEMO_DIR/$file" ]]; then
        err "Dashboard file not found: $DEMO_DIR/$file"
        exit 1
    fi

    log "Starting $version dashboard on port $port..."
    cd "$DEMO_DIR"
    streamlit run "$file" --server.port "$port" --server.headless true \
        > "$PID_DIR/dashboard.log" 2>&1 &
    echo $! > "$PID_DIR/dashboard.pid"
    sleep 2

    if kill -0 "$(cat "$PID_DIR/dashboard.pid")" 2>/dev/null; then
        log "Dashboard ready at ${CYAN}http://localhost:$port${NC}"
    else
        err "Dashboard failed to start. Check $PID_DIR/dashboard.log"
        cat "$PID_DIR/dashboard.log"
        exit 1
    fi
}

# ---- main ----

usage() {
    echo ""
    echo -e "${CYAN}Nereus Platform Launcher${NC}"
    echo ""
    echo "Usage: ./launch.sh <version|command>"
    echo ""
    echo "  Dashboards (starts API + dashboard):"
    echo "    v4    Intelligence Platform - 9 sites, 6 tabs    (port 8504)"
    echo "    v3    Intelligence Platform - 2 sites, 5 tabs    (port 8503)"
    echo "    v2    Live Dashboard - 2 sites                   (port 8501)"
    echo "    v1    Static Dashboard - bundle only, no API     (port 8500)"
    echo ""
    echo "  Services:"
    echo "    api   API server only                            (port 8000)"
    echo "    stop  Stop all running services"
    echo ""
}

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

VERSION="$1"

case "$VERSION" in
    v1)
        load_env
        stop_all
        log "v1 is static - no API needed"
        start_dashboard v1
        echo ""
        log "Nereus v1 (static) running at ${CYAN}http://localhost:$(get_port v1)${NC}"
        echo -e "  Press Ctrl+C to stop"
        wait
        ;;
    v2|v3|v4)
        load_env
        stop_all

        # Check Neo4j
        log "Checking Neo4j connectivity..."
        neo_result=$(check_neo4j)
        if [[ "$neo_result" == "ok" ]]; then
            log "Neo4j connected (${MARIS_NEO4J_URI:-bolt://localhost:7687})"
        else
            warn "Neo4j unavailable: ${neo_result#fail:}"
            warn "Dashboard will run in demo mode (precomputed responses)"
        fi

        start_api
        start_dashboard "$VERSION"

        dash_port=$(get_port "$VERSION")
        echo ""
        log "Nereus $VERSION is live:"
        echo -e "  API:       ${CYAN}http://localhost:$API_PORT${NC}"
        echo -e "  Dashboard: ${CYAN}http://localhost:$dash_port${NC}"
        echo -e "  Neo4j:     ${CYAN}http://localhost:7474${NC}"
        echo ""
        echo -e "  Press Ctrl+C to stop all services"
        trap stop_all EXIT INT TERM
        wait
        ;;
    api)
        load_env
        stop_service "api"
        start_api
        echo ""
        log "API server running at ${CYAN}http://localhost:$API_PORT/api/health${NC}"
        echo -e "  Press Ctrl+C to stop"
        trap 'stop_service api' EXIT INT TERM
        wait
        ;;
    stop)
        load_env
        stop_all
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        err "Unknown version: $VERSION"
        usage
        exit 1
        ;;
esac
