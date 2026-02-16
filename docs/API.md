# Java Migration Central - CLI API Reference

## Overview

Complete command reference for the Java Migration Central Platform CLI.

## Installation

```bash
python3 migration-platform.py --help
./platform.sh --help
```

---

## Platform Management Commands

### `create-templates`
Initialize platform with default templates and configuration.

```bash
python3 migration-platform.py create-templates
```

**Output:**
- Creates `templates/` directory
- Generates `renovate.template.json`
- Generates `rewrite.template.yml`
- Generates `github-actions.template.yml`
- Generates `migration-config.template.yml`

**Example:**
```bash
python3 migration-platform.py create-templates
# ✅ Created migration template at templates/migration-config.template.yml
```

---

### `status`
Display platform status and statistics.

```bash
python3 migration-platform.py status
./platform.sh status
```

**Output:**
```
JAVA MIGRATION CENTRAL PLATFORM - STATUS
======================================================================
📊 Total Repositories: 400

📈 Status Breakdown:
  • PENDING: 180
  • IN_PROGRESS: 80
  • COMPLETED: 120
  • FAILED: 20
  • BLOCKED: 0

🎯 Migration Targets:
  • Java 11: 150 repositories
  • Java 17: 100 repositories
  • Java 21: 100 repositories
  • Java 25: 50 repositories

🔨 Build Systems:
  • MAVEN: 350 repositories
  • GRADLE: 50 repositories

======================================================================
```

---

## Repository Management

### `register`
Register a single repository.

```bash
python3 migration-platform.py register \
  --url <repository-url> \
  --current-version <version> \
  --target-version <version>
```

**Parameters:**
- `--url` (required): Repository URL
- `--current-version` (required): Current Java version (8, 11, 17, 21)
- `--target-version` (required): Target Java version (11, 17, 21, 25)

**Example:**
```bash
python3 migration-platform.py register \
  --url https://github.com/myorg/api-service \
  --current-version 8 \
  --target-version 11
# ✅ Registered repository: api-service
```

---

### `register-batch`
Register multiple repositories from CSV file.

```bash
python3 migration-platform.py register-batch --csv <csv-file>
./platform.sh register-batch --csv repositories.csv
```

**Parameters:**
- `--csv` (required): Path to CSV file

**CSV Format:**
```csv
url,name,current_version,target_version,tags
https://github.com/org/app1,app1,8,11,critical
https://github.com/org/app2,app2,8,11,production
```

**Example:**
```bash
./platform.sh register-batch --csv repositories.csv
# Batch registration: 150/150 successful
```

---

### `validate-repos`
Validate repositories in CSV before registration.

```bash
python3 migration-platform.py validate-repos --csv <csv-file>
```

**Parameters:**
- `--csv` (required): Path to CSV file

**Output:**
```
Validating repositories...
✅ 150 repositories valid
✅ All URLs accessible
✅ Ready for registration
```

---

### `list-repos`
List all registered repositories.

```bash
python3 migration-platform.py list-repos
./platform.sh list-repos
```

**Output:**
```
Registered Repositories
==============================
Total: 400

Java 8 → 11 (150):
  • api-service-1: COMPLETED
  • api-service-2: IN_PROGRESS
  • web-app-1: PENDING
  ...

Java 11 → 17 (100):
  • data-service-1: PENDING
  ...
```

---

### `repo-status`
Show status of a specific repository.

```bash
python3 migration-platform.py repo-status --repo-name <name>
./platform.sh repo-status --repo <name>
```

**Parameters:**
- `--repo-name` or `--repo` (required): Repository name

**Output:**
```
Repository: api-service-1
URL: https://github.com/org/api-service-1
Status: IN_PROGRESS
Migration: Java 8 → 11
Last Updated: 2026-02-16 14:30:00

Details:
  Build System: Maven
  Tests: RUNNING
  Code Quality: PASSED
  Next Step: Integration tests
```

---

## Migration Execution

### `migrate-batch`
Start batch migration for multiple repositories.

```bash
python3 migration-platform.py migrate-batch \
  --source-version <version> \
  --target-version <version> \
  --parallel-workers <number> \
  --job-id <id>

./platform.sh migrate-batch \
  --source <version> \
  --target <version> \
  --workers <number>
```

**Parameters:**
- `--source-version` (required): Source Java version
- `--target-version` (required): Target Java version
- `--parallel-workers` (default: 20): Number of concurrent migrations
- `--job-id` (optional): Custom job identifier

**Example:**
```bash
./platform.sh migrate-batch --source 8 --target 11 --workers 20
# 🚀 Starting batch migration: java8to11-phase1
# Repositories: 150
# Workers: 20
# ... migration in progress ...
```

---

### `watch-batch`
Monitor batch migration progress in real-time.

```bash
python3 migration-platform.py watch-batch \
  --job-id <id> \
  --refresh-interval <seconds>

./platform.sh watch-batch --job-id <id>
```

**Parameters:**
- `--job-id` (required): Job identifier from migrate-batch
- `--refresh-interval` (default: 30): Seconds between updates

**Output:**
```
Job: java8to11-phase1
Migration: Java 8 → 11

Progress: 75/150 (50%)
├─ Completed: 60 ✅
├─ In Progress: 15 ⏳
└─ Failed: 5 ❌

Recent Activity:
├─ ✅ api-service-15: Tests passed
├─ ⏳ web-app-8: Running integration tests
└─ ❌ auth-service-3: Compilation error

[Refreshing in 30 seconds...]
```

---

### `list-jobs`
List all migration jobs.

```bash
python3 migration-platform.py list-jobs
./platform.sh list-jobs
```

**Output:**
```
Migration Jobs
==========================
1. java8to11-phase1
   Status: IN_PROGRESS
   Progress: 50% (75/150)
   Duration: 2h 30m

2. java11to17-phase2
   Status: PENDING
   Progress: 0% (0/100)
```

---

### `job-status`
Show detailed status of a specific job.

```bash
python3 migration-platform.py job-status --job-id <id>
./platform.sh job-status --job-id <id>
```

**Parameters:**
- `--job-id` (required): Job identifier

---

## Reporting

### `report`
Generate migration reports.

```bash
python3 migration-platform.py report --type <type> --format <format>
./platform.sh report --type <type>
```

**Parameters:**
- `--type` (default: executive-summary): Report type
  - `executive-summary`: High-level overview
  - `detailed`: Complete technical report
  - `failure-report`: Analysis of failures
- `--format` (default: json): Output format
  - `json`: Structured data
  - `html`: Web-readable
  - `markdown`: Markdown format
- `--output` (optional): Output file path

**Example:**
```bash
./platform.sh report --type executive-summary
# 📊 Report saved to reports/migration-report-20260216-143000.json
```

**Executive Summary Output:**
```json
{
  "report_type": "Executive Summary",
  "timestamp": "2026-02-16 15:30:00",
  "total_repositories": 400,
  "migration_status": {
    "completed": 120,
    "in_progress": 80,
    "pending": 180,
    "failed": 20,
    "completion_rate": "30%"
  },
  "key_metrics": {
    "avg_migration_time_days": 3.2,
    "success_rate": "98%",
    "critical_failures": 2
  }
}
```

---

## Troubleshooting

### `list-failed`
List failed migrations.

```bash
python3 migration-platform.py list-failed \
  --source-version <version> \
  --target-version <version>

./platform.sh list-failed
```

**Output:**
```
Failed Migrations
==================
Total: 5

1. auth-service-3
   Error: Package javax.servlet not found
   Migration: 8-to-11

2. payment-svc-2
   Error: Conflicting dependency versions
   Migration: 8-to-11
```

---

### `failure-details`
Show detailed failure information.

```bash
python3 migration-platform.py failure-details --repo-name <name>
./platform.sh failure-details --repo <name>
```

**Parameters:**
- `--repo-name` or `--repo` (required): Repository name

**Output:**
```
Failure Details: auth-service-3
==============================

Error: Package javax.servlet not found
Migration: Java 8 → 11

Stack Trace:
[compilation error details]

Recommendation:
Update imports: javax → jakarta

Build Log:
[relevant build log excerpt]
```

---

### `retry-failed`
Retry failed migrations.

```bash
python3 migration-platform.py retry-failed \
  --source-version <version> \
  --target-version <version> \
  --limit <number> \
  --parallel-workers <number>
```

**Parameters:**
- `--source-version` (optional): Filter by source version
- `--target-version` (optional): Filter by target version
- `--limit` (default: 10): Max migrations to retry
- `--parallel-workers` (default: 5): Concurrent workers

**Example:**
```bash
python3 migration-platform.py retry-failed --limit 5
# Retrying 5 failed migrations...
# ✅ Retry complete: 4 succeeded, 1 still failing
```

---

### `retry-repo`
Force retry for a specific repository.

```bash
python3 migration-platform.py retry-repo --repo-name <name>
```

**Parameters:**
- `--repo-name` (required): Repository name

---

### `logs`
View logs for a repository.

```bash
python3 migration-platform.py logs --repo-name <name>
./platform.sh logs --repo <name>
```

**Parameters:**
- `--repo-name` or `--repo` (required): Repository name

**Output:**
```
Logs for: api-service-1
==========================================
[timestamp] - Starting migration...
[timestamp] - Running Renovate...
[timestamp] - Updating dependencies...
[timestamp] - Running OpenRewrite...
[timestamp] - Compilation successful
[timestamp] - Tests passed
[timestamp] - Migration complete
```

---

## Setup Automation

### `setup-all`
Setup all automation (Renovate, OpenRewrite, GitHub Actions).

```bash
python3 migration-platform.py setup-all \
  --repos <filter>
```

**Parameters:**
- `--repos` (default: all): Repository filter
  - `all`: All repositories
  - `java-8-to-11`: Java 8 → 11 migrations only
  - `java-11-to-17`: Java 11 → 17 migrations only

---

### `setup-renovate`
Setup Renovate for repositories.

```bash
python3 migration-platform.py setup-renovate \
  --all-repos \
  --schedule <schedule>
```

**Parameters:**
- `--all-repos`: Apply to all repositories
- `--schedule`: Update schedule (e.g., "before 3am on Monday")

---

### `setup-openrewrite`
Setup OpenRewrite for repositories.

```bash
python3 migration-platform.py setup-openrewrite \
  --all-repos \
  --target-version <version>
```

---

### `setup-github-actions`
Setup GitHub Actions workflows.

```bash
python3 migration-platform.py setup-github-actions \
  --all-repos \
  --slack-webhook <url>
```

**Parameters:**
- `--all-repos`: Apply to all repositories
- `--slack-webhook`: Slack webhook for notifications

---

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: File not found
- `4`: Registration failed
- `5`: Migration failed

---

## Environment Variables

```bash
# Custom config directory
export JAVA_MIGRATION_CONFIG_DIR="/path/to/config"

# Log level
export LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR

# Slack webhook (for notifications)
export SLACK_WEBHOOK="https://hooks.slack.com/..."

# GitHub token (for API access)
export GITHUB_TOKEN="ghp_..."
```

---

## Examples

### Complete Migration Workflow

```bash
# 1. Initialize
python3 migration-platform.py create-templates

# 2. Register repositories
./platform.sh register-batch --csv repositories.csv

# 3. Check status
./platform.sh status

# 4. Start migration
./platform.sh migrate-batch --source 8 --target 11 --workers 20

# 5. Monitor
./platform.sh watch-batch --job-id java8to11-phase1

# 6. Generate report
./platform.sh report --type executive-summary

# 7. Retry failures (if any)
python3 migration-platform.py retry-failed --limit 10
```

### Quick Status Check

```bash
./platform.sh status
./platform.sh list-jobs
./platform.sh report --type executive-summary
```

### Troubleshoot Specific App

```bash
./platform.sh repo-status --repo my-app
./platform.sh failure-details --repo my-app
./platform.sh logs --repo my-app
python3 migration-platform.py retry-repo --repo-name my-app
```

---

## Help & Support

```bash
# Show help
./platform.sh help
python3 migration-platform.py --help

# Get detailed command help
./platform.sh migrate-batch --help
python3 migration-platform.py migrate-batch --help
```

---

For more information, see:
- [SETUP.md](SETUP.md) - Setup guide
- [PLATFORM_GUIDE.md](PLATFORM_GUIDE.md) - Complete guide
- [../README.md](../README.md) - Project README

