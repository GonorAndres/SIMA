#!/usr/bin/env bash
# ============================================================
# GCP Cloud Run Command Center
# Universal control panel for ALL Cloud Run services
# Auto-discovers services -- works with any future deployments
# ============================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
PROJECT="project-ad7a5be2-a1c7-4510-82d"

# ── Colors ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Helper functions ───────────────────────────────────────

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${BOLD}  GCP Cloud Run Command Center${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo -e "  Project:  ${BOLD}${PROJECT}${NC}"
    echo -e "${CYAN}------------------------------------------------------------${NC}"
}

# List all Cloud Run services as JSON array
list_services_json() {
    gcloud run services list \
        --project="$PROJECT" \
        --format="json" 2>/dev/null
}

# Get a flat list of "SERVICE REGION URL" lines
list_services_flat() {
    gcloud run services list \
        --project="$PROJECT" \
        --format="value(metadata.name, metadata.labels.'cloud.googleapis.com/location', status.url)" \
        2>/dev/null
}

# Check if a specific service allows unauthenticated access
is_public() {
    local service="$1" region="$2"
    local policy
    policy=$(gcloud run services get-iam-policy "$service" \
        --region="$region" \
        --project="$PROJECT" \
        --format="json" 2>/dev/null)
    echo "$policy" | grep -q '"allUsers"' && return 0 || return 1
}

# Resolve service name to region (auto-discover)
resolve_region() {
    local service="$1"
    gcloud run services list \
        --project="$PROJECT" \
        --filter="metadata.name=$service" \
        --format="value(metadata.labels.'cloud.googleapis.com/location')" \
        2>/dev/null
}

# Resolve service URL
resolve_url() {
    local service="$1"
    gcloud run services list \
        --project="$PROJECT" \
        --filter="metadata.name=$service" \
        --format="value(status.url)" \
        2>/dev/null
}

# Validate that a service exists, exit with error if not
require_service() {
    local service="$1"
    local region
    region=$(resolve_region "$service")
    if [ -z "$region" ]; then
        echo -e "${RED}ERROR: Service '${service}' not found in project ${PROJECT}${NC}"
        echo -e "Run ${BOLD}./cloud-control.sh list${NC} to see available services."
        exit 1
    fi
    echo "$region"
}

# Print status row for one service
print_service_row() {
    local service="$1" region="$2" url="$3"
    local access_label

    if is_public "$service" "$region"; then
        access_label="${GREEN}PUBLIC ${NC}"
    else
        access_label="${YELLOW}PRIVATE${NC}"
    fi

    printf "  %-20s %-16s %b   %s\n" "$service" "$region" "$access_label" "$url"
}

# Detailed status for one service
print_service_detail() {
    local service="$1" region="$2"

    local description
    description=$(gcloud run services describe "$service" \
        --region="$region" \
        --project="$PROJECT" \
        --format="json" 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "  ${RED}ERROR: Could not describe service ${service}${NC}"
        return 1
    fi

    local url latest_revision max_instances memory conditions
    url=$(echo "$description" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('status', {}).get('url', 'unknown'))
" 2>/dev/null || echo "unknown")

    latest_revision=$(echo "$description" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('status', {}).get('latestReadyRevisionName', 'unknown'))
" 2>/dev/null || echo "unknown")

    max_instances=$(echo "$description" | python3 -c "
import sys, json
d = json.load(sys.stdin)
ann = d.get('spec', {}).get('template', {}).get('metadata', {}).get('annotations', {})
print(ann.get('autoscaling.knative.dev/maxScale', 'default'))
" 2>/dev/null || echo "unknown")

    memory=$(echo "$description" | python3 -c "
import sys, json
d = json.load(sys.stdin)
containers = d.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [{}])
res = containers[0].get('resources', {}).get('limits', {})
print(res.get('memory', 'unknown'))
" 2>/dev/null || echo "unknown")

    conditions=$(echo "$description" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for c in d.get('status', {}).get('conditions', []):
    s = c.get('status', 'Unknown')
    print(f\"  {c['type']}: {s}\")
" 2>/dev/null || echo "  Could not parse conditions")

    echo ""
    echo -e "  ${BOLD}${service}${NC} ${DIM}(${region})${NC}"
    echo -e "${CYAN}  ----------------------------------------------------------${NC}"

    echo -ne "  Access:         "
    if is_public "$service" "$region"; then
        echo -e "${GREEN}PUBLIC${NC} (anyone can access)"
    else
        echo -e "${YELLOW}PRIVATE${NC} (GCP project members only)"
    fi

    echo -e "  URL:            ${BOLD}${url}${NC}"
    echo -e "  Revision:       ${latest_revision}"
    echo -e "  Max instances:  ${max_instances}"
    echo -e "  Memory:         ${memory}"
    echo ""
    echo -e "  ${BOLD}Conditions:${NC}"
    echo "$conditions"

    # Health check (try common paths)
    echo ""
    echo -ne "  Health:         "
    local health_code
    health_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 "${url}/" 2>/dev/null || echo "000")

    if [ "$health_code" = "200" ]; then
        echo -e "${GREEN}HEALTHY${NC} (HTTP 200)"
    elif [ "$health_code" = "403" ]; then
        echo -e "${YELLOW}RESTRICTED${NC} (HTTP 403 - private, but service is up)"
    elif [ "$health_code" = "000" ]; then
        echo -e "${RED}UNREACHABLE${NC} (timeout or cold start)"
    else
        echo -e "${RED}HTTP ${health_code}${NC}"
    fi
}

# ── Commands ───────────────────────────────────────────────

cmd_list() {
    print_header
    echo ""
    echo -e "  ${BOLD}SERVICE              REGION           ACCESS    URL${NC}"
    echo -e "${CYAN}  ----------------------------------------------------------${NC}"

    local found=0
    while IFS=$'\t' read -r service region url; do
        [ -z "$service" ] && continue
        print_service_row "$service" "$region" "$url"
        found=1
    done < <(list_services_flat)

    if [ "$found" -eq 0 ]; then
        echo -e "  ${DIM}No Cloud Run services found in project.${NC}"
    fi
    echo ""
}

cmd_status() {
    local target="${1:-}"
    print_header

    if [ -z "$target" ]; then
        # Status for ALL services
        local found=0
        while IFS=$'\t' read -r service region url; do
            [ -z "$service" ] && continue
            print_service_detail "$service" "$region"
            found=1
        done < <(list_services_flat)

        if [ "$found" -eq 0 ]; then
            echo -e "  ${DIM}No Cloud Run services found.${NC}"
        fi
    else
        # Status for ONE service
        local region
        region=$(require_service "$target")
        print_service_detail "$target" "$region"
    fi
    echo ""
}

cmd_public() {
    local target="${1:-}"

    if [ -z "$target" ]; then
        echo -e "${RED}ERROR: Specify a service name.${NC}"
        echo -e "Usage: ./cloud-control.sh public <service>"
        echo -e "Run ${BOLD}./cloud-control.sh list${NC} to see services."
        exit 1
    fi

    local region
    region=$(require_service "$target")

    print_header
    echo ""

    if is_public "$target" "$region"; then
        echo -e "  ${BOLD}${target}${NC} is ${GREEN}already PUBLIC${NC}. No changes needed."
        echo ""
        return 0
    fi

    echo -e "  Making ${BOLD}${target}${NC} PUBLIC..."
    gcloud run services add-iam-policy-binding "$target" \
        --region="$region" \
        --project="$PROJECT" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --quiet > /dev/null 2>&1

    local url
    url=$(resolve_url "$target")
    echo -e "  Access changed to: ${GREEN}PUBLIC${NC}"
    echo -e "  URL: ${BOLD}${url}${NC}"
    echo ""
}

cmd_private() {
    local target="${1:-}"

    if [ -z "$target" ]; then
        echo -e "${RED}ERROR: Specify a service name.${NC}"
        echo -e "Usage: ./cloud-control.sh private <service>"
        echo -e "Run ${BOLD}./cloud-control.sh list${NC} to see services."
        exit 1
    fi

    local region
    region=$(require_service "$target")

    print_header
    echo ""

    if ! is_public "$target" "$region"; then
        echo -e "  ${BOLD}${target}${NC} is ${YELLOW}already PRIVATE${NC}. No changes needed."
        echo ""
        return 0
    fi

    echo -e "  Making ${BOLD}${target}${NC} PRIVATE..."
    gcloud run services remove-iam-policy-binding "$target" \
        --region="$region" \
        --project="$PROJECT" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --quiet > /dev/null 2>&1

    echo -e "  Access changed to: ${YELLOW}PRIVATE${NC}"
    echo -e "  (Only GCP project members can access)"
    echo ""
}

cmd_public_all() {
    print_header
    echo ""
    echo -e "  ${BOLD}Making ALL services PUBLIC...${NC}"
    echo ""

    while IFS=$'\t' read -r service region url; do
        [ -z "$service" ] && continue
        if is_public "$service" "$region"; then
            echo -e "  ${service}: ${GREEN}already public${NC}"
        else
            gcloud run services add-iam-policy-binding "$service" \
                --region="$region" \
                --project="$PROJECT" \
                --member="allUsers" \
                --role="roles/run.invoker" \
                --quiet > /dev/null 2>&1
            echo -e "  ${service}: ${GREEN}now PUBLIC${NC}"
        fi
    done < <(list_services_flat)
    echo ""
}

cmd_private_all() {
    print_header
    echo ""
    echo -e "  ${BOLD}Making ALL services PRIVATE...${NC}"
    echo ""

    while IFS=$'\t' read -r service region url; do
        [ -z "$service" ] && continue
        if ! is_public "$service" "$region"; then
            echo -e "  ${service}: ${YELLOW}already private${NC}"
        else
            gcloud run services remove-iam-policy-binding "$service" \
                --region="$region" \
                --project="$PROJECT" \
                --member="allUsers" \
                --role="roles/run.invoker" \
                --quiet > /dev/null 2>&1
            echo -e "  ${service}: ${YELLOW}now PRIVATE${NC}"
        fi
    done < <(list_services_flat)
    echo ""
}

cmd_logs() {
    local target="${1:-}"
    local lines="${2:-50}"

    if [ -z "$target" ]; then
        echo -e "${RED}ERROR: Specify a service name.${NC}"
        echo -e "Usage: ./cloud-control.sh logs <service> [lines]"
        exit 1
    fi

    local region
    region=$(require_service "$target")

    echo -e "${BOLD}Fetching last ${lines} log entries for ${target}...${NC}"
    echo ""
    gcloud run services logs read "$target" \
        --region="$region" \
        --project="$PROJECT" \
        --limit="$lines"
}

cmd_help() {
    print_header
    echo ""
    echo -e "  ${BOLD}Usage:${NC}  ./cloud-control.sh <command> [service] [args]"
    echo ""
    echo -e "  ${BOLD}Discovery:${NC}"
    echo -e "    ${GREEN}list${NC}                      List all services with access status"
    echo -e "    ${GREEN}status${NC}                    Detailed status of ALL services"
    echo -e "    ${GREEN}status${NC} ${DIM}<service>${NC}          Detailed status of one service"
    echo ""
    echo -e "  ${BOLD}Single service:${NC}"
    echo -e "    ${GREEN}public${NC} ${DIM}<service>${NC}          Make one service public"
    echo -e "    ${GREEN}private${NC} ${DIM}<service>${NC}         Make one service private"
    echo -e "    ${GREEN}logs${NC} ${DIM}<service>${NC} ${DIM}[N]${NC}        Show last N log lines (default 50)"
    echo ""
    echo -e "  ${BOLD}Bulk operations:${NC}"
    echo -e "    ${GREEN}public-all${NC}                Make ALL services public"
    echo -e "    ${GREEN}private-all${NC}               Make ALL services private"
    echo ""
    echo -e "  ${BOLD}Examples:${NC}"
    echo -e "    ./cloud-control.sh list                # See everything"
    echo -e "    ./cloud-control.sh status sima         # Deep status for sima"
    echo -e "    ./cloud-control.sh public sima         # Open sima for demo"
    echo -e "    ./cloud-control.sh private sima        # Lock sima down"
    echo -e "    ./cloud-control.sh public-all          # Open all for demo"
    echo -e "    ./cloud-control.sh private-all         # Lock everything down"
    echo -e "    ./cloud-control.sh logs sima 100       # Last 100 log lines"
    echo ""
}

# ── Main dispatch ──────────────────────────────────────────

case "${1:-help}" in
    list)         cmd_list ;;
    status)       cmd_status "${2:-}" ;;
    public)       cmd_public "${2:-}" ;;
    private)      cmd_private "${2:-}" ;;
    public-all)   cmd_public_all ;;
    private-all)  cmd_private_all ;;
    logs)         cmd_logs "${2:-}" "${3:-50}" ;;
    help|-h|--help) cmd_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
