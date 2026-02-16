#!/bin/bash
################################################################################
# Centralized Java Migration Platform - CLI Wrapper
# Manages 400+ Java applications migration automatically
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/migration-platform.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

show_help() {
    cat << 'EOF'
Centralized Java Migration Platform - CLI

USAGE:
    ./platform.sh [COMMAND] [OPTIONS]

COMMANDS:

  Platform Management:
    status                  Show platform status and statistics
    create-templates        Initialize migration templates
    list-repos              List all registered repositories

  Repository Management:
    register                Register a single repository
      --url <url>          Repository URL (required)
      --current <version>  Current Java version (required)
      --target <version>   Target Java version (required)

    register-batch          Register multiple repositories from CSV
      --csv <file>         CSV file path (required)

    validate-repos          Validate repositories before registration
      --csv <file>         CSV file path (required)

    repo-status             Show specific repository status
      --repo <name>        Repository name (required)

  Migration Execution:
    migrate-batch           Start batch migration
      --source <version>   Source Java version (required)
      --target <version>   Target Java version (required)
      --workers <n>        Parallel workers (default: 20)
      --job-id <id>        Job ID (optional)

    watch-batch             Watch batch migration progress
      --job-id <id>        Job ID (required)
      --interval <n>       Refresh interval in seconds (default: 30)

    retry-failed            Retry failed migrations
      --limit <n>          Max retries (default: 10)

    list-failed             List failed migrations
      --source <version>   Source version (optional)
      --target <version>   Target version (optional)

  Setup Automation:
    setup-all               Setup all automation for all repos
    setup-renovate          Setup Renovate for all repos
    setup-openrewrite       Setup OpenRewrite for all repos
    setup-github-actions    Setup GitHub Actions for all repos

  Reporting:
    report                  Generate migration report
      --type <type>        Report type: executive-summary, detailed, failure-report
      --format <format>    Format: json, html, markdown (default: json)

    list-jobs               List all migration jobs
    job-status              Show job status
      --job-id <id>        Job ID (required)

  Troubleshooting:
    logs                    Show logs for repository
      --repo <name>        Repository name (required)

    failure-details         Show failure details
      --repo <name>        Repository name (required)

    help                    Show this help message

EXAMPLES:

  1. Initialize platform:
     ./platform.sh create-templates

  2. Register repositories from CSV:
     ./platform.sh register-batch --csv repositories.csv

  3. Check status:
     ./platform.sh status

  4. Start Java 8→11 migration for 20 apps in parallel:
     ./platform.sh migrate-batch --source 8 --target 11 --workers 20

  5. Monitor migration progress:
     ./platform.sh watch-batch --job-id java8to11-phase1

  6. Generate report:
     ./platform.sh report --type executive-summary

EOF
}

# Main CLI
COMMAND=${1:-help}

case $COMMAND in
    status)
        print_header "Java Migration Platform - Status"
        python3 "$PYTHON_SCRIPT" status
        ;;

    create-templates)
        print_header "Creating Migration Templates"
        python3 "$PYTHON_SCRIPT" create-templates
        print_success "Templates created successfully"
        ;;

    register)
        URL=${2:-}
        CURRENT=${3:-}
        TARGET=${4:-}

        if [ -z "$URL" ] || [ -z "$CURRENT" ] || [ -z "$TARGET" ]; then
            print_error "Usage: ./platform.sh register <url> <current-version> <target-version>"
            exit 1
        fi

        print_info "Registering repository: $URL"
        python3 "$PYTHON_SCRIPT" register --url "$URL" --current-version "$CURRENT" --target-version "$TARGET"
        ;;

    register-batch)
        CSV=${2:-}
        if [ -z "$CSV" ]; then
            print_error "Usage: ./platform.sh register-batch <csv-file>"
            exit 1
        fi

        if [ ! -f "$CSV" ]; then
            print_error "CSV file not found: $CSV"
            exit 1
        fi

        print_header "Batch Registration"
        print_info "File: $CSV"

        # Count repos
        COUNT=$(tail -n +2 "$CSV" | wc -l)
        print_info "Repositories to register: $COUNT"

        python3 "$PYTHON_SCRIPT" register-batch --csv "$CSV"
        ;;

    list-repos)
        print_header "Registered Repositories"
        python3 "$PYTHON_SCRIPT" list-repos
        ;;

    repo-status)
        REPO=${2:-}
        if [ -z "$REPO" ]; then
            print_error "Usage: ./platform.sh repo-status <repo-name>"
            exit 1
        fi

        print_header "Repository Status: $REPO"
        python3 "$PYTHON_SCRIPT" repo-status --repo "$REPO"
        ;;

    migrate-batch)
        SOURCE=${2:-}
        TARGET=${3:-}
        WORKERS=${4:-20}

        if [ -z "$SOURCE" ] || [ -z "$TARGET" ]; then
            print_error "Usage: ./platform.sh migrate-batch <source> <target> [workers]"
            exit 1
        fi

        print_header "Starting Batch Migration"
        print_info "Source: Java $SOURCE"
        print_info "Target: Java $TARGET"
        print_info "Workers: $WORKERS"

        python3 "$PYTHON_SCRIPT" migrate-batch --source "$SOURCE" --target "$TARGET" --workers "$WORKERS"
        ;;

    watch-batch)
        JOB_ID=${2:-}
        if [ -z "$JOB_ID" ]; then
            print_error "Usage: ./platform.sh watch-batch <job-id>"
            exit 1
        fi

        print_header "Watching Migration Progress"
        while true; do
            clear
            echo ""
            python3 "$PYTHON_SCRIPT" job-status --job-id "$JOB_ID"
            echo ""
            print_info "Refreshing in 30 seconds... (Ctrl+C to stop)"
            sleep 30
        done
        ;;

    report)
        TYPE=${2:-executive-summary}
        print_header "Generating Migration Report"
        print_info "Type: $TYPE"
        python3 "$PYTHON_SCRIPT" report --type "$TYPE"
        ;;

    list-jobs)
        print_header "Migration Jobs"
        python3 "$PYTHON_SCRIPT" list-jobs
        ;;

    list-failed)
        print_header "Failed Migrations"
        python3 "$PYTHON_SCRIPT" list-failed
        ;;

    help|--help|-h)
        show_help
        ;;

    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac

