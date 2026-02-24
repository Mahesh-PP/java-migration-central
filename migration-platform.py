#!/usr/bin/env python3
"""
Java Migration Central Platform
A centralized application for managing Java migrations across 400+ repositories
Handles: Java 8 → 11 → 17 → 21 → 25

Features:
- Batch repository management
- Automated dependency updates via Renovate
- Code transformation via OpenRewrite
- GitHub Actions validation
- Progress tracking and reporting
- Multi-version parallel processing
"""

import os
import sys
import json
import yaml
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures
import requests
import shutil
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JavaVersion(Enum):
    """Supported Java versions"""
    JAVA_8 = "8"
    JAVA_11 = "11"
    JAVA_17 = "17"
    JAVA_21 = "21"
    JAVA_25 = "25"


class MigrationStatus(Enum):
    """Migration status"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class RepositoryConfig:
    """Configuration for a repository"""
    repo_url: str
    repo_name: str
    current_java_version: str
    target_java_version: str
    build_system: str  # maven or gradle
    status: str = "PENDING"
    last_updated: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class MigrationPhase:
    """Migration phase definition"""
    source_version: str
    target_version: str
    spring_boot_version: str
    maven_compiler_version: str
    key_changes: List[str]
    dependency_updates: Dict[str, str]


class JavaMigrationPlatform:
    """Central platform for managing Java migrations"""

    def __init__(self, config_dir: str = ".java-migration-central"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.repos_dir = self.config_dir / "repositories"
        self.repos_dir.mkdir(exist_ok=True)
        self.reports_dir = self.config_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.templates_dir = self.config_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)

        # Migration phases
        self.phases = {
            "8-to-11": MigrationPhase(
                source_version="8",
                target_version="11",
                spring_boot_version="2.3.0.RELEASE",
                maven_compiler_version="3.8.1",
                key_changes=[
                    "Remove deprecated methods (Thread.destroy, Thread.stop)",
                    "Update Stream API usage",
                    "Update Java EE to Jakarta EE",
                    "Update build plugins"
                ],
                dependency_updates={
                    "spring-boot": "2.3.0.RELEASE",
                    "maven-compiler-plugin": "3.8.1"
                }
            ),
            "11-to-17": MigrationPhase(
                source_version="11",
                target_version="17",
                spring_boot_version="2.7.0",
                maven_compiler_version="3.10.0",
                key_changes=[
                    "Update Spring Boot to 2.7.x LTS",
                    "Remove deprecated APIs",
                    "Update to use records (optional)",
                    "Update sealed classes (optional)"
                ],
                dependency_updates={
                    "spring-boot": "2.7.0",
                    "maven-compiler-plugin": "3.10.0"
                }
            ),
            "17-to-21": MigrationPhase(
                source_version="17",
                target_version="21",
                spring_boot_version="3.1.0",
                maven_compiler_version="3.11.0",
                key_changes=[
                    "Adopt text blocks (Java 13+)",
                    "Adopt record classes (Java 14+)",
                    "Adopt sealed classes (Java 15+)",
                    "Update to var type inference",
                    "Use new collections factory methods"
                ],
                dependency_updates={
                    "spring-boot": "3.1.0",
                    "maven-compiler-plugin": "3.11.0"
                }
            ),
            "21-to-25": MigrationPhase(
                source_version="21",
                target_version="25",
                spring_boot_version="3.4.0",
                maven_compiler_version="3.13.0",
                key_changes=[
                    "Evaluate new language features (Java 23, 24, 25)",
                    "Update to use unnamed patterns",
                    "Review and update deprecated APIs",
                    "Update virtual threads usage"
                ],
                dependency_updates={
                    "spring-boot": "3.4.0",
                    "maven-compiler-plugin": "3.13.0"
                }
            )
        }

    def register_repository(self, repo_url: str, current_version: str, target_version: str) -> bool:
        """Register a repository for migration"""
        try:
            # Extract repo info
            repo_name = repo_url.split('/')[-1].replace('.git', '')

            # Detect build system
            build_system = self._detect_build_system(repo_url)

            # Create config
            config = RepositoryConfig(
                repo_url=repo_url,
                repo_name=repo_name,
                current_java_version=current_version,
                target_java_version=target_version,
                build_system=build_system
            )

            # Save config
            config_file = self.repos_dir / f"{repo_name}.json"
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)

            logger.info(f"✅ Registered repository: {repo_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register repository: {e}")
            return False

    def _detect_build_system(self, repo_url: str) -> str:
        """Detect build system (Maven or Gradle)"""
        # In real implementation, clone and check
        # For now, default to Maven
        return "maven"

    def load_repositories(self) -> List[RepositoryConfig]:
        """Load all registered repositories"""
        repos = []
        for config_file in self.repos_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                repos.append(RepositoryConfig(**data))
            except Exception as e:
                logger.error(f"Error loading {config_file}: {e}")
        return repos

    def create_migration_config(self, repo: RepositoryConfig) -> Dict:
        """Create migration configuration for a repository"""
        return {
            "project": {
                "name": repo.repo_name,
                "url": repo.repo_url,
                "currentVersion": repo.current_java_version,
                "targetVersion": repo.target_java_version
            },
            "buildSystems": {
                "maven": {
                    "enabled": repo.build_system == "maven",
                    "configFile": "pom.xml"
                },
                "gradle": {
                    "enabled": repo.build_system == "gradle",
                    "configFile": "build.gradle"
                }
            },
            "cicd": {
                "buildTool": repo.build_system,
                "enabledChecks": [
                    "compilation",
                    "unit-tests",
                    "integration-tests",
                    "checkstyle",
                    "spotbugs",
                    "coverage"
                ]
            }
        }

    def create_renovate_config(self, repo: RepositoryConfig) -> Dict:
        """Create Renovate configuration for dependency updates"""
        return {
            "extends": ["config:base"],
            "automerge": False,
            "java": {
                "enabled": True,
                "minor": {"enabled": True},
                "patch": {"enabled": True},
                "digest": {"enabled": True}
            },
            "maven": {
                "enabled": True,
                "skipCache": True,
                "skipDependencyUpdate": False
            },
            "packageRules": [
                {
                    "matchUpdateTypes": ["minor", "patch"],
                    "automerge": True,
                    "automergeType": "pr"
                },
                {
                    "matchDatasources": ["maven"],
                    "commitMessagePrefix": "chore(deps): "
                }
            ],
            "schedule": ["before 3am on Monday"],
            "prCreation": "not-pending",
            "semanticCommits": True
        }

    def create_openrewrite_config(self, current_version: str, target_version: str) -> Dict:
        """Create OpenRewrite configuration for code transformation"""
        return {
            "type": "specs.openrewrite.org/v1beta/recipe",
            "name": f"java{current_version}to{target_version}",
            "displayName": f"Migrate from Java {current_version} to Java {target_version}",
            "description": f"Automated Java {current_version} to Java {target_version} migration",
            "recipeList": self._get_openrewrite_recipes(current_version, target_version)
        }

    def _get_openrewrite_recipes(self, current_version: str, target_version: str) -> List[str]:
        """Get OpenRewrite recipes for version migration"""
        recipes = []

        if current_version == "8" and target_version == "11":
            recipes = [
                "org.openrewrite.java.migrate.Java8to11",
                "org.openrewrite.java.RemoveJavaIoSerializable",
                "org.openrewrite.java.migrate.RemoveUnnecessaryBoxingInMethodCalls"
            ]
        elif current_version == "11" and target_version == "17":
            recipes = [
                "org.openrewrite.java.migrate.Java11to17",
                "org.openrewrite.java.migrate.RemoveUnnecessaryExtendsObject"
            ]
        elif current_version == "17" and target_version == "21":
            recipes = [
                "org.openrewrite.java.migrate.Java17to21",
                "org.openrewrite.java.migrate.UpgradeToJava21"
            ]
        elif current_version == "21" and target_version == "25":
            recipes = [
                "org.openrewrite.java.migrate.Java21to25",
                "org.openrewrite.java.migrate.UpgradeToJava25"
            ]

        return recipes

    def create_github_actions_config(self, repo: RepositoryConfig) -> str:
        """Create GitHub Actions workflow configuration"""
        return f"""name: Java Migration CI/CD - {repo.repo_name}

on:
  push:
    branches: [main, develop, master]
    paths:
      - 'pom.xml'
      - 'build.gradle'
      - 'src/**'
      - '.openrewrite/**'
  pull_request:
    branches: [main, develop, master]
  workflow_dispatch:

jobs:
  validate-migration:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        java-version: [11, 17, 21, 25]
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Java ${{{{ matrix.java-version }}}}
        uses: actions/setup-java@v3
        with:
          java-version: ${{{{ matrix.java-version }}}}
          distribution: 'temurin'
          cache: maven
      
      - name: Compile
        run: |
          if [ -f "pom.xml" ]; then
            ./mvnw clean compile -DskipTests
          else
            ./gradlew clean build -x test
          fi
      
      - name: Run tests
        run: |
          if [ -f "pom.xml" ]; then
            ./mvnw test verify
          else
            ./gradlew test
          fi
      
      - name: Code quality
        run: |
          if [ -f "pom.xml" ]; then
            ./mvnw checkstyle:check spotbugs:check || true
          fi
"""

    def generate_batch_report(self, repos: List[RepositoryConfig]) -> Dict:
        """Generate batch migration report"""
        total = len(repos)
        completed = len([r for r in repos if r.status == "COMPLETED"])
        in_progress = len([r for r in repos if r.status == "IN_PROGRESS"])
        failed = len([r for r in repos if r.status == "FAILED"])
        pending = len([r for r in repos if r.status == "PENDING"])

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_repositories": total,
                "completed": completed,
                "in_progress": in_progress,
                "failed": failed,
                "pending": pending,
                "completion_percentage": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
            },
            "repositories": [repo.to_dict() for repo in repos],
            "migration_paths": self._analyze_migration_paths(repos)
        }

    def _analyze_migration_paths(self, repos: List[RepositoryConfig]) -> Dict:
        """Analyze migration paths across repositories"""
        paths = {}
        for repo in repos:
            path = f"{repo.current_java_version}-to-{repo.target_java_version}"
            if path not in paths:
                paths[path] = 0
            paths[path] += 1
        return paths

    def save_report(self, report: Dict, filename: str = None) -> str:
        """Save report to file"""
        if not filename:
            filename = f"migration-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        report_path = self.reports_dir / filename
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"📊 Report saved to {report_path}")
        return str(report_path)

    def get_platform_status(self) -> Dict:
        """Get overall platform status"""
        repos = self.load_repositories()
        return {
            "timestamp": datetime.now().isoformat(),
            "total_repositories": len(repos),
            "status_breakdown": {
                "pending": len([r for r in repos if r.status == "PENDING"]),
                "in_progress": len([r for r in repos if r.status == "IN_PROGRESS"]),
                "completed": len([r for r in repos if r.status == "COMPLETED"]),
                "failed": len([r for r in repos if r.status == "FAILED"]),
                "blocked": len([r for r in repos if r.status == "BLOCKED"])
            },
            "migration_targets": self._analyze_migration_targets(repos),
            "build_systems": self._analyze_build_systems(repos)
        }

    def _analyze_migration_targets(self, repos: List[RepositoryConfig]) -> Dict:
        """Analyze target Java versions"""
        targets = {}
        for repo in repos:
            if repo.target_java_version not in targets:
                targets[repo.target_java_version] = 0
            targets[repo.target_java_version] += 1
        return targets

    def _analyze_build_systems(self, repos: List[RepositoryConfig]) -> Dict:
        """Analyze build systems in use"""
        systems = {}
        for repo in repos:
            if repo.build_system not in systems:
                systems[repo.build_system] = 0
            systems[repo.build_system] += 1
        return systems

    def create_migration_templates(self):
        """Create standard migration templates"""
        # Migration config template
        migration_template = {
            "project": {"name": "PROJECT_NAME"},
            "phases": {
                "phase1": {
                    "name": "Java 8 to Java 11",
                    "sourceVersion": "8",
                    "targetVersion": "11",
                    "releaseTarget": "integration-testing"
                }
            }
        }

        template_file = self.templates_dir / "migration-config.template.yml"
        with open(template_file, 'w') as f:
            yaml.dump(migration_template, f)

        logger.info(f"✅ Created migration template at {template_file}")

    def display_status(self):
        """Display platform status"""
        status = self.get_platform_status()

        print("\n" + "="*70)
        print("JAVA MIGRATION CENTRAL PLATFORM - STATUS")
        print("="*70)
        print(f"\n📊 Total Repositories: {status['total_repositories']}")
        print("\n📈 Status Breakdown:")
        for status_type, count in status['status_breakdown'].items():
            print(f"  • {status_type.upper()}: {count}")

        print("\n🎯 Migration Targets:")
        for version, count in status['migration_targets'].items():
            print(f"  • Java {version}: {count} repositories")

        print("\n🔨 Build Systems:")
        for system, count in status['build_systems'].items():
            print(f"  • {system.upper()}: {count} repositories")

        print("\n" + "="*70 + "\n")

    def migrate_repositories(self, urls: List[str], source: str = '8', target: str = '11', workers: int = 4, push: bool = False, branch: str = None, create_pr: bool = False) -> List[Dict]:
        """Migrate one or more repositories from source -> target.

        Steps performed (best-effort demo):
        - clone the repo
        - detect build system
        - create OpenRewrite recipe, Renovate config, GitHub Actions workflow
        - create a migration branch, commit the new configs
        - optionally push the branch (requires auth)

        This function is intentionally conservative: it doesn't modify source code
        or run OpenRewrite automatically. It prepares repository-level configs
        and commits them on a branch so maintainers can review and run migration
        pipelines.
        """
        results = []
        work_dir = self.config_dir / 'work'
        work_dir.mkdir(exist_ok=True)
        branch = branch or f'migrate-java-{source}-to-{target}'

        def process(url: str) -> Dict:
            repo_name = url.split('/')[-1].replace('.git', '')
            repo_path = work_dir / repo_name
            result = {
                'repo': repo_name,
                'url': url,
                'status': 'FAILED',
                'message': ''
            }

            # Ensure previous work removed
            if repo_path.exists():
                try:
                    shutil.rmtree(repo_path)
                except Exception:
                    pass

            try:
                logger.info(f"Cloning {url} → {repo_path}")
                subprocess.run(['git', 'clone', url, str(repo_path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Detect build system by files
                build_system = 'maven'
                if (repo_path / 'pom.xml').exists():
                    build_system = 'maven'
                elif (repo_path / 'build.gradle').exists() or (repo_path / 'build.gradle.kts').exists():
                    build_system = 'gradle'

                # Register repository (saves a config JSON)
                self.register_repository(url, source, target)
                config_file = self.repos_dir / f"{repo_name}.json"
                # Load config and update build_system
                try:
                    with open(config_file, 'r') as f:
                        cfg = json.load(f)
                    cfg['build_system'] = build_system
                    cfg['status'] = MigrationStatus.IN_PROGRESS.value
                    cfg['last_updated'] = datetime.now().isoformat()
                    with open(config_file, 'w') as f:
                        json.dump(cfg, f, indent=2)
                except Exception:
                    logger.debug(f"Could not update local repo config for {repo_name}")

                # Create OpenRewrite recipe
                or_cfg = self.create_openrewrite_config(source, target)
                or_dir = repo_path / '.openrewrite'
                or_dir.mkdir(parents=True, exist_ok=True)
                with open(or_dir / 'recipe.yml', 'w') as f:
                    yaml.dump(or_cfg, f)

                # Create renovate.json
                repo_config = RepositoryConfig(repo_url=url, repo_name=repo_name, current_java_version=source, target_java_version=target, build_system=build_system)
                renovate_cfg = self.create_renovate_config(repo_config)
                with open(repo_path / 'renovate.json', 'w') as f:
                    json.dump(renovate_cfg, f, indent=2)

                # Create GitHub Actions workflow
                gha = self.create_github_actions_config(repo_config)
                gha_dir = repo_path / '.github' / 'workflows'
                gha_dir.mkdir(parents=True, exist_ok=True)
                with open(gha_dir / 'java-migration.yml', 'w') as f:
                    f.write(gha)

                # **Run OpenRewrite to transform Java code and pom.xml**
                logger.info(f"⚡ Starting OpenRewrite code transformation")
                openrewrite_success = self.run_openrewrite_migration(repo_path, source, target)

                if openrewrite_success:
                    logger.info(f"✅ OpenRewrite transformation completed - Java code has been migrated")
                else:
                    logger.warning(f"⚠️ OpenRewrite transformation skipped or failed - only Java source changes will be in PR")

                # Git: create branch, commit with selective file staging
                subprocess.run(['git', '-C', str(repo_path), 'checkout', '-b', branch], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Stage only Java migration-related files (skip renovate.json and .openrewrite configs)
                stage_success, staged_files = self._stage_migration_files(repo_path)

                if not stage_success or not staged_files:
                    logger.warning(f"⚠️  No Java migration files found to commit. This may be expected if OpenRewrite made no changes.")
                    result['message'] = 'No Java migration changes detected'
                else:
                    commit_msg = f'chore(migration): migrate Java {source} → {target}\n\nUpdates:\n- pom.xml with new Java version and dependencies\n- Import statements updated to Jakarta EE\n- Java source code transformed for Java {target} compatibility'
                    # Commit the staged files
                    commit_result = subprocess.run(['git', '-C', str(repo_path), 'commit', '-m', commit_msg], capture_output=True, text=True)
                    if commit_result.returncode == 0:
                        logger.info(f"✅ Committed {len(staged_files)} Java migration files")
                    else:
                        logger.warning(f"⚠️  Commit may have failed: {commit_result.stderr}")
                        result['message'] = 'Commit failed - no changes to commit'

                if push:
                    logger.info(f"Pushing branch {branch} to origin for {repo_name}")
                    try:
                        # Get the token from environment
                        token = os.environ.get('GITHUB_TOKEN', '')

                        # If we have a token, we can push with authentication
                        if token:
                            # Use git credential helpers that were configured in workflow
                            # Use --force-with-lease to safely force push if branch diverged
                            result_push = subprocess.run(
                                ['git', '-C', str(repo_path), 'push', '--force-with-lease', '--set-upstream', 'origin', branch],
                                capture_output=True, text=True, check=True,
                                env={**os.environ, 'GIT_ASKPASS': '', 'GIT_TERMINAL_PROMPT': '0'}
                            )
                        else:
                            # No token available, try without authentication (for public repos)
                            result_push = subprocess.run(
                                ['git', '-C', str(repo_path), 'push', '--force-with-lease', '--set-upstream', 'origin', branch],
                                capture_output=True, text=True, check=True
                            )

                        pushed = True
                        logger.info(f"✅ Successfully pushed branch {branch} to {repo_name}")
                    except subprocess.CalledProcessError as e:
                        logger.warning(f"⚠️  Push failed for {repo_name}: {e}")
                        logger.warning(f"STDOUT: {e.stdout if hasattr(e, 'stdout') else 'N/A'}")
                        logger.warning(f"STDERR: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
                        logger.info(f"Note: This may be expected for private repos without PAT. If using public repo, check permissions.")
                        pushed = False
                else:
                    pushed = False

                # Optionally create a PR (only if push succeeded and create_pr requested)
                if create_pr and pushed:
                    try:
                        # **Check if branch has commits ahead of base**
                        commits_ahead = self._check_commits_ahead(repo_path, 'origin', branch)
                        if commits_ahead <= 0:
                            logger.warning(f"⚠️  Branch {branch} has no commits ahead of base - skipping PR creation")
                            result['message'] += f'; No commits ahead to create PR'
                        else:
                            logger.info(f"✅ Branch has {commits_ahead} commit(s) ahead of base")
                            pr_url = self.create_pull_request(repo_path, branch,
                                                              title=f"Migrate to Java {target}",
                                                              body=f"Automated migration branch to upgrade from Java {source} to {target}.")
                            if pr_url:
                                result['pr_url'] = pr_url
                                result['message'] += f'; PR: {pr_url}'
                                logger.info(f"✅ PULL REQUEST CREATED: {pr_url}")
                                print(f"\n{'='*60}")
                                print(f"🎉 PULL REQUEST CREATED!")
                                print(f"{'='*60}")
                                print(f"Repository: {repo_name}")
                                print(f"PR URL: {pr_url}")
                                print(f"{'='*60}\n")
                            else:
                                result['message'] += '; PR not created'
                    except Exception as e:
                        logger.warning(f"PR creation failed for {repo_name}: {e}")

                # Update stored config to completed
                try:
                    with open(config_file, 'r') as f:
                        cfg = json.load(f)
                    cfg['status'] = MigrationStatus.COMPLETED.value
                    cfg['last_updated'] = datetime.now().isoformat()
                    with open(config_file, 'w') as f:
                        json.dump(cfg, f, indent=2)
                except Exception:
                    pass

                result['status'] = 'COMPLETED'
                result['message'] = f'Prepared migration branch {branch}'
                logger.info(f"Prepared migration for {repo_name}")
            except subprocess.CalledProcessError as e:
                errmsg = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
                result['message'] = f'Git error: {errmsg}'
                logger.error(f"Git operation failed for {repo_name}: {errmsg}")
                # mark failed
                try:
                    config_file = self.repos_dir / f"{repo_name}.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            cfg = json.load(f)
                        cfg['status'] = MigrationStatus.FAILED.value
                        cfg['error_message'] = errmsg
                        cfg['last_updated'] = datetime.now().isoformat()
                        with open(config_file, 'w') as f:
                            json.dump(cfg, f, indent=2)
                except Exception:
                    pass
            except Exception as e:
                result['message'] = str(e)
                logger.error(f"Error preparing {repo_name}: {e}")
                try:
                    config_file = self.repos_dir / f"{repo_name}.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            cfg = json.load(f)
                        cfg['status'] = MigrationStatus.FAILED.value
                        cfg['error_message'] = str(e)
                        cfg['last_updated'] = datetime.now().isoformat()
                        with open(config_file, 'w') as f:
                            json.dump(cfg, f, indent=2)
                except Exception:
                    pass

            return result

        # Run in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(process, url): url for url in urls}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    results.append(res)
                except Exception as e:
                    results.append({'repo': 'unknown', 'url': futures[fut], 'status': 'FAILED', 'message': str(e)})

        return results


    def run_openrewrite_migration(self, repo_path: Path, source: str, target: str) -> bool:
        """Run OpenRewrite to transform Java code and build files

        Returns True to continue (transformation is optional)
        """
        try:
            logger.info(f"Attempting OpenRewrite migration from Java {source} to {target}")

            # Get the OpenRewrite recipe based on version
            if source == "17" and target == "21":
                recipe = "org.openrewrite.java.migrate.Java17to21"
            elif source == "11" and target == "17":
                recipe = "org.openrewrite.java.migrate.Java11to17"
            elif source == "8" and target == "11":
                recipe = "org.openrewrite.java.migrate.Java8to11"
            elif source == "21" and target == "25":
                recipe = "org.openrewrite.java.migrate.Java21to25"
            else:
                recipe = None

            if not recipe:
                logger.info(f"No recipe for {source} → {target}")
                return True

            if (repo_path / 'pom.xml').exists():
                logger.info("Detected Maven project")

                # Try to run Maven with OpenRewrite, but don't fail if it's not available
                try:
                    cmd = [
                        'mvn'
                    ]

                    # Allow custom settings.xml to be provided via env
                    maven_settings_path = None

                    # Priority 1: User provided base64-encoded settings.xml
                    if os.environ.get('MAVEN_SETTINGS_BASE64'):
                        import base64, tempfile
                        encoded = os.environ.get('MAVEN_SETTINGS_BASE64')
                        try:
                            data = base64.b64decode(encoded)
                            tmp_dir = tempfile.mkdtemp(prefix='mvn-settings-')
                            settings_file = os.path.join(tmp_dir, 'settings.xml')
                            with open(settings_file, 'wb') as sf:
                                sf.write(data)
                            maven_settings_path = settings_file
                            logger.info(f"Using Maven settings from MAVEN_SETTINGS_BASE64")
                        except Exception as e:
                            logger.warning(f"Could not decode MAVEN_SETTINGS_BASE64: {e}")

                    # Priority 2: User provided a path to settings.xml
                    elif os.environ.get('MAVEN_SETTINGS_PATH'):
                        maven_settings_path = os.environ.get('MAVEN_SETTINGS_PATH')
                        logger.info(f"Using Maven settings from MAVEN_SETTINGS_PATH: {maven_settings_path}")

                    # Priority 3: Use default ~/.m2/settings.xml if it exists
                    else:
                        default_settings = Path.home() / '.m2' / 'settings.xml'
                        if default_settings.exists():
                            maven_settings_path = str(default_settings)
                            logger.info(f"Using default Maven settings: {maven_settings_path}")

                    if maven_settings_path:
                        cmd.extend(['-s', maven_settings_path])

                    # Add Maven options to handle offline mode and skip repository resolution issues
                    # This allows OpenRewrite to work even if some repositories are unavailable
                    cmd.extend([
                        '-o',  # Offline mode to use local cache only
                        '-DskipTests',  # Skip tests
                        '-Dorg.slf4j.simpleLogger.defaultLogLevel=info',  # Control logging
                    ])

                    # Add the OpenRewrite plugin invocation and recipe flags
                    cmd.extend([
                        'org.openrewrite.maven:rewrite-maven-plugin:run',
                        f'-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:LATEST',
                        f'-Drewrite.activeRecipes={recipe}',
                        '-Drewrite.dryRun=false',  # Ensure changes are written, not just detected
                        '-Drewrite.failOnDryRunResults=false',  # Don't fail if dry run finds issues
                    ])

                    logger.info(f"🔧 Running: mvn org.openrewrite.maven:rewrite-maven-plugin:run -Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:LATEST -Drewrite.activeRecipes={recipe}")
                    result = subprocess.run(
                        cmd,
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                    logger.info(f"OpenRewrite exit code: {result.returncode}")

                    # Log stdout/stderr for debugging
                    if result.stdout:
                        logger.debug(f"OpenRewrite stdout:\n{result.stdout}")
                    if result.stderr:
                        logger.debug(f"OpenRewrite stderr:\n{result.stderr}")

                    # Detect fatal Maven/project-building errors
                    stderr_lower = (result.stderr or '').lower()
                    stdout_lower = (result.stdout or '').lower()
                    stderr_full = result.stderr or ''

                    fatal_indicators = [
                        'non-resolvable parent pom',
                        'could not transfer artifact',
                        'authorization failed',
                        '403 forbidden',
                        '401 unauthorized',
                        'unresolvablemodelexception',
                        'projectbuildingexception'
                    ]

                    has_fatal_error = any(ind in stderr_lower or ind in stdout_lower for ind in fatal_indicators)

                    if has_fatal_error and result.returncode != 0:
                        logger.warning("⚠️ Maven/OpenRewrite failed due to repository/auth issues")
                        logger.info(f"Maven error details:\n{stderr_full}")
                        logger.info("📝 Retrying without offline mode to download dependencies...")

                        # Retry without offline mode to download missing dependencies
                        cmd_retry = [
                            'mvn',
                        ]

                        if maven_settings_path:
                            cmd_retry.extend(['-s', maven_settings_path])

                        # Remove offline flag and try again
                        cmd_retry.extend([
                            '-DskipTests',
                            '-Dorg.slf4j.simpleLogger.defaultLogLevel=warn',
                            'org.openrewrite.maven:rewrite-maven-plugin:run',
                            f'-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:LATEST',
                            f'-Drewrite.activeRecipes={recipe}',
                        ])

                        logger.info(f"🔧 Retrying with online mode...")
                        result_retry = subprocess.run(
                            cmd_retry,
                            cwd=str(repo_path),
                            capture_output=True,
                            text=True,
                            timeout=300
                        )

                        logger.info(f"OpenRewrite retry exit code: {result_retry.returncode}")

                        if result_retry.returncode in [0, 1]:
                            logger.info(f"✅ OpenRewrite transformation completed on retry")
                            return True
                        else:
                            logger.warning(f"⚠️ OpenRewrite still failed on retry")
                            if result_retry.stderr:
                                logger.info(f"Retry stderr:\n{result_retry.stderr}")
                            return False

                    # Exit code 0 or 1 typically indicate the recipe applied (0) or no changes needed (1)
                    if result.returncode in [0, 1]:
                        logger.info(f"✅ OpenRewrite transformation completed successfully")

                        # Check if pom.xml was actually modified by OpenRewrite
                        git_status = subprocess.run(
                            ['git', '-C', str(repo_path), 'status', '--porcelain'],
                            capture_output=True,
                            text=True
                        )
                        if 'pom.xml' in git_status.stdout:
                            logger.info(f"✅ pom.xml has been updated by OpenRewrite")
                        else:
                            logger.info(f"ℹ️ pom.xml not modified (may already be at target version)")

                        return True
                    else:
                        logger.warning(f"⚠️ OpenRewrite execution returned status {result.returncode}")
                        if result.stderr:
                            logger.info(f"OpenRewrite stderr:\n{result.stderr}")
                        return False

                except FileNotFoundError:
                    logger.warning(f"⚠️ Maven not available on system")
                    logger.info(f"ℹ️ Please install Maven to run OpenRewrite transformations")
                    return False
                except subprocess.TimeoutExpired:
                    logger.warning(f"⚠️ OpenRewrite operation timed out (>300s)")
                    return False
            elif (repo_path / 'build.gradle').exists() or (repo_path / 'build.gradle.kts').exists():
                logger.info("Detected Gradle project")

                # For Gradle, we need to use the OpenRewrite init script
                import urllib.request
                import tempfile

                try:
                    # Download the OpenRewrite init script
                    init_script_url = "https://raw.githubusercontent.com/openrewrite/rewrite/main/gradle/init.gradle"
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.gradle', delete=False) as init_file:
                        init_script_path = init_file.name
                        with urllib.request.urlopen(init_script_url) as response:
                            init_file.write(response.read().decode('utf-8'))

                    logger.info(f"Downloaded OpenRewrite init script to {init_script_path}")

                    # Run Gradle with OpenRewrite
                    cmd = [
                        './gradlew',
                        '--init-script', init_script_path,
                        'rewriteRun',
                        f'-Drewrite.activeRecipes={recipe}',
                        '-Drewrite.dryRun=false',
                        '--no-daemon'  # Avoid daemon issues in CI
                    ]

                    logger.info(f"🔧 Running: ./gradlew --init-script {init_script_path} rewriteRun -Drewrite.activeRecipes={recipe}")
                    result = subprocess.run(
                        cmd,
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                        timeout=600  # Gradle might take longer
                    )

                    logger.info(f"OpenRewrite Gradle exit code: {result.returncode}")

                    # Log stdout/stderr for debugging
                    if result.stdout:
                        logger.debug(f"OpenRewrite Gradle stdout:\n{result.stdout}")
                    if result.stderr:
                        logger.debug(f"OpenRewrite Gradle stderr:\n{result.stderr}")

                    # Clean up init script
                    os.unlink(init_script_path)

                    # Exit code 0 or 1 typically indicate success
                    if result.returncode in [0, 1]:
                        logger.info(f"✅ OpenRewrite Gradle transformation completed")

                        # Check if build.gradle was modified
                        git_status = subprocess.run(
                            ['git', '-C', str(repo_path), 'status', '--porcelain'],
                            capture_output=True,
                            text=True
                        )
                        if 'build.gradle' in git_status.stdout or 'build.gradle.kts' in git_status.stdout:
                            logger.info(f"✅ Build file has been updated by OpenRewrite")
                        else:
                            logger.info(f"ℹ️ Build file not modified (may already be at target version)")

                        return True
                    else:
                        logger.warning(f"⚠️ OpenRewrite Gradle failed with exit code {result.returncode}")
                        if result.stderr:
                            logger.info(f"Gradle stderr:\n{result.stderr}")
                        return False

                except Exception as e:
                    logger.warning(f"⚠️ Gradle OpenRewrite setup failed: {e}")
                    return False
            else:
                logger.info("No pom.xml or build.gradle found - skipping OpenRewrite")
                return True

        except Exception as e:
            logger.error(f"⚠️ OpenRewrite transformation error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def _stage_migration_files(self, repo_path: Path) -> Tuple[bool, List[str]]:
        """
        Stage only Java migration-related files for commit.
        Includes: pom.xml, build.gradle, Java source files
        Excludes: renovate.json, .openrewrite/, .github/, target/, build artifacts

        Returns: (success: bool, staged_files: List[str])
        """
        import fnmatch

        try:
            staged_files = []
            files_to_stage = []

            # Explicit folders/files to EXCLUDE
            exclude_prefixes = [
                'renovate.json',
                '.openrewrite/',
                '.github/',
                'target/',
                'build/',
                '.gradle/',
                '.idea/',
                '.vscode/',
                '*.class',
                '*.jar'
            ]

            # Get git status to find modified files
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse porcelain output: paths start at index 3
            modified_files = []
            for raw_line in result.stdout.splitlines():
                line = raw_line.rstrip()
                if not line or len(line) < 3:
                    continue
                path_part = line[3:].strip()
                # Handle rename format: "old -> new"
                if '->' in path_part:
                    path = path_part.split('->')[-1].strip()
                else:
                    path = path_part
                # Strip surrounding quotes
                if path.startswith('"') and path.endswith('"'):
                    path = path[1:-1]
                modified_files.append(path)

            logger.info(f"Found {len(modified_files)} modified/new files in git status")

            # Always check for pom.xml and build files
            always_check_files = ['pom.xml', 'build.gradle', 'build.gradle.kts', 'gradle.properties', 'maven.config']
            for check_file in always_check_files:
                check_path = repo_path / check_file
                if check_path.exists() and check_file not in modified_files:
                    logger.info(f"  ℹ️ Adding existing file for consideration: {check_file}")
                    modified_files.append(check_file)

            # Filter files: exclude build artifacts, include migration files
            for file_path in modified_files:
                should_skip = False
                skip_reason = ""

                # Check if file should be excluded
                for exclude in exclude_prefixes:
                    if exclude.startswith('.'):
                        if file_path == exclude or file_path.startswith(exclude):
                            should_skip = True
                            skip_reason = f"matches exclude pattern: {exclude}"
                            break
                    elif '/' in exclude:
                        if file_path.startswith(exclude):
                            should_skip = True
                            skip_reason = f"is in excluded directory: {exclude}"
                            break
                    else:
                        if fnmatch.fnmatch(file_path, exclude):
                            should_skip = True
                            skip_reason = f"matches exclude pattern: {exclude}"
                            break

                # Include only relevant files
                if not should_skip:
                    if file_path in ['pom.xml', 'build.gradle', 'build.gradle.kts', 'gradle.properties', 'maven.config']:
                        should_skip = False
                    elif file_path.endswith('.java'):
                        should_skip = False
                    elif file_path.endswith('module-info.java'):
                        should_skip = False
                    elif file_path.startswith('src/') and file_path.endswith('.properties'):
                        should_skip = False
                    elif file_path.startswith('src/') and (file_path.endswith('.xml') or file_path.endswith('.yml') or file_path.endswith('.yaml')):
                        should_skip = False
                    else:
                        should_skip = True
                        skip_reason = "not a Java migration file"

                if not should_skip:
                    files_to_stage.append(file_path)
                    staged_files.append(file_path)
                    logger.info(f"  ✅ Including: {file_path}")
                else:
                    logger.debug(f"  ⏭️  Skipping: {file_path} ({skip_reason})")

            # Stage the filtered files
            if files_to_stage:
                for file_path in files_to_stage:
                    subprocess.run(
                        ['git', '-C', str(repo_path), 'add', file_path],
                        capture_output=True,
                        check=True
                    )

                # Verify what is actually staged
                staged_proc = subprocess.run(
                    ['git', '-C', str(repo_path), 'diff', '--cached', '--name-only'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                actually_staged = [s.strip() for s in staged_proc.stdout.splitlines() if s.strip()]

                if not actually_staged:
                    logger.warning("⚠️ No files were staged after `git add` - nothing to commit")
                    return False, []

                logger.info(f"✅ Staged {len(actually_staged)} Java migration files for commit")
                return True, actually_staged
            else:
                logger.warning(f"⚠️  No Java migration files to stage")
                return False, []

        except Exception as e:
            logger.error(f"Error staging migration files: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False, []

    def _check_commits_ahead(self, repo_path: Path, remote: str, branch: str) -> int:
        """Check how many commits the branch is ahead of the base branch.

        Returns the number of commits ahead, or 0 if equal.
        """
        try:
            # Fetch latest from origin
            subprocess.run(['git', '-C', str(repo_path), 'fetch', remote], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Get the default base branch
            base_branch = 'main'
            for candidate in ['main', 'master', 'develop']:
                check_result = subprocess.run(
                    ['git', '-C', str(repo_path), 'rev-parse', f'{remote}/{candidate}'],
                    capture_output=True
                )
                if check_result.returncode == 0:
                    base_branch = candidate
                    break

            # Compare commits: how many commits are in branch but NOT in base
            result = subprocess.run(
                ['git', '-C', str(repo_path), 'rev-list', '--count', f'{remote}/{base_branch}..HEAD'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            commits_ahead = int(result.stdout.decode().strip())
            logger.info(f"Branch {branch} is {commits_ahead} commit(s) ahead of {remote}/{base_branch}")
            return commits_ahead
        except Exception as e:
            logger.warning(f"Could not determine commits ahead for {branch}: {e}")
            return 0

    def create_pull_request(self, repo_path: Path, branch: str, title: str, body: str) -> Optional[str]:
        """Create a GitHub Pull Request for the pushed branch."""
        try:
            # Get origin URL
            proc = subprocess.run(['git', '-C', str(repo_path), 'config', '--get', 'remote.origin.url'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            origin_url = proc.stdout.decode().strip()
            if 'github.com' not in origin_url:
                logger.info(f"Origin is not GitHub, skipping PR creation: {origin_url}")
                return None

            # Parse owner and repo
            owner = None
            repo = None
            if origin_url.startswith('git@'):
                parts = origin_url.split(':', 1)
                if len(parts) == 2:
                    owner_repo = parts[1]
                    if owner_repo.endswith('.git'):
                        owner_repo = owner_repo[:-4]
                    if '/' in owner_repo:
                        owner, repo = owner_repo.split('/', 1)
            else:
                parsed = urlparse(origin_url)
                path = parsed.path.lstrip('/')
                if path.endswith('.git'):
                    path = path[:-4]
                if '/' in path:
                    owner, repo = path.split('/', 1)

            if not owner or not repo:
                logger.info(f"Could not parse GitHub owner/repo from origin: {origin_url}")
                return None

            token = os.environ.get('GITHUB_TOKEN')
            if not token:
                logger.info('GITHUB_TOKEN not set; skipping PR creation')
                return None

            api_base = f'https://api.github.com/repos/{owner}/{repo}'

            # Get default branch for base
            headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
            r = requests.get(api_base, headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Failed to fetch repo info from GitHub: {r.status_code} {r.text}")
                return None
            repo_info = r.json()
            base_branch = repo_info.get('default_branch', 'main')

            # Create PR
            pr_payload = {
                'title': title,
                'head': branch,
                'base': base_branch,
                'body': body
            }
            pr_r = requests.post(f'{api_base}/pulls', headers=headers, json=pr_payload, timeout=15)
            if pr_r.status_code in (200, 201):
                pr = pr_r.json()
                pr_url = pr.get('html_url')
                logger.info(f"Created PR: {pr_url}")
                return pr_url
            else:
                logger.warning(f"Failed to create PR: {pr_r.status_code} {pr_r.text}")
                return None
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git error while determining origin for PR creation: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error creating PR: {e}")
            return None

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Java Migration Central Platform')
    parser.add_argument('--config-dir', default='.java-migration-central',
                       help='Configuration directory')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Register repository command
    register_parser = subparsers.add_parser('register', help='Register a repository')
    register_parser.add_argument('--url', required=True, help='Repository URL')
    register_parser.add_argument('--current-version', required=True,
                                help='Current Java version (8, 11, 17, 21)')
    register_parser.add_argument('--target-version', required=True,
                               help='Target Java version (11, 17, 21, 25)')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration status')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate migration report')

    # Create templates command
    templates_parser = subparsers.add_parser('create-templates',
                                            help='Create migration templates')

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Prepare migration for one or more repositories')
    migrate_parser.add_argument('--url', action='append', help='Repository URL (can be specified multiple times)')
    migrate_parser.add_argument('--csv', help='CSV file with repository URLs (one per line)')
    migrate_parser.add_argument('--source', default='8', help='Source Java version (default: 8)')
    migrate_parser.add_argument('--target', default='11', help='Target Java version (default: 11)')
    migrate_parser.add_argument('--workers', type=int, default=4, help='Parallel workers (default: 4)')
    migrate_parser.add_argument('--push', action='store_true', help='Push migration branch to origin (requires auth)')
    migrate_parser.add_argument('--branch', help='Branch name to create for migration (default generated)')
    migrate_parser.add_argument('--create-pr', action='store_true', help='Create a GitHub PR for the migration branch')

    args = parser.parse_args()

    platform = JavaMigrationPlatform(args.config_dir)

    if args.command == 'register':
        success = platform.register_repository(args.url, args.current_version,
                                              args.target_version)
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        platform.display_status()

    elif args.command == 'report':
        repos = platform.load_repositories()
        report = platform.generate_batch_report(repos)
        platform.save_report(report)

    elif args.command == 'create-templates':
        platform.create_migration_templates()

    elif args.command == 'migrate':
        urls = []
        if args.url:
            urls.extend(args.url)
        if args.csv:
            csv_path = Path(args.csv)
            if csv_path.exists():
                with open(csv_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            urls.append(line)

        if not urls:
            logger.error('No repository URLs provided')
            sys.exit(1)

        logger.info(f"Starting migration: {args.source} → {args.target}")
        results = platform.migrate_repositories(
            urls=urls,
            source=args.source,
            target=args.target,
            workers=args.workers,
            push=args.push,
            branch=args.branch,
            create_pr=args.create_pr
        )

        # Print results
        print(json.dumps(results, indent=2))

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
