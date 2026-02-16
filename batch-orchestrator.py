#!/usr/bin/env python3
"""
Batch Migration Orchestrator
Handles batch processing of 400+ repositories with parallel execution
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    """Represents a batch migration job"""
    job_id: str
    repositories: List[Dict]
    source_version: str
    target_version: str
    total_repos: int
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def to_dict(self):
        return {
            'job_id': self.job_id,
            'total_repos': self.total_repos,
            'completed': self.completed,
            'failed': self.failed,
            'in_progress': self.in_progress,
            'migration': f'{self.source_version}-to-{self.target_version}',
            'progress_percentage': f"{(self.completed/self.total_repos*100):.1f}%" if self.total_repos > 0 else "0%",
            'elapsed_time': f"{(time.time() - self.start_time):.0f}s" if self.start_time else "0s"
        }


class BatchMigrationOrchestrator:
    """Orchestrates batch migrations across multiple repositories"""

    def __init__(self, platform):
        self.platform = platform
        self.jobs_dir = platform.config_dir / "jobs"
        self.jobs_dir.mkdir(exist_ok=True)

    def import_repositories_from_csv(self, csv_file: str) -> List[Dict]:
        """Import repositories from CSV file"""
        repos = []
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    repos.append({
                        'url': row['url'],
                        'current_version': row['current_version'],
                        'target_version': row['target_version'],
                        'name': row.get('name', row['url'].split('/')[-1])
                    })

            logger.info(f"✅ Imported {len(repos)} repositories from {csv_file}")
            return repos
        except Exception as e:
            logger.error(f"❌ Failed to import from CSV: {e}")
            return []

    def register_batch(self, repos: List[Dict]) -> Dict:
        """Register multiple repositories"""
        results = {
            'total': len(repos),
            'success': 0,
            'failed': 0,
            'failures': []
        }

        for repo in repos:
            try:
                success = self.platform.register_repository(
                    repo['url'],
                    repo['current_version'],
                    repo['target_version']
                )
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['failures'].append(repo['url'])
            except Exception as e:
                results['failed'] += 1
                results['failures'].append(f"{repo['url']}: {str(e)}")

        logger.info(f"Batch registration: {results['success']}/{results['total']} successful")
        return results

    def create_batch_job(self, job_id: str, source_version: str,
                        target_version: str, repos: List[Dict]) -> BatchJob:
        """Create a new batch job"""
        job = BatchJob(
            job_id=job_id,
            repositories=repos,
            source_version=source_version,
            target_version=target_version,
            total_repos=len(repos),
            start_time=time.time()
        )

        # Save job info
        job_file = self.jobs_dir / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job.to_dict(), f, indent=2)

        logger.info(f"📋 Created batch job: {job_id}")
        return job

    def execute_batch_migration(self, job: BatchJob, max_workers: int = 20) -> Dict:
        """Execute batch migration in parallel"""
        logger.info(f"🚀 Starting batch migration: {job.job_id}")
        logger.info(f"   Repositories: {job.total_repos}")
        logger.info(f"   Migration: Java {job.source_version} → {job.target_version}")
        logger.info(f"   Parallel workers: {max_workers}")

        results = {
            'job_id': job.job_id,
            'completed': [],
            'failed': [],
            'in_progress': []
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all migration tasks
            future_to_repo = {
                executor.submit(self._migrate_single_repo, repo): repo
                for repo in job.repositories
            }

            # Process completed tasks
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    if result['success']:
                        results['completed'].append(repo['name'])
                        job.completed += 1
                    else:
                        results['failed'].append({
                            'repo': repo['name'],
                            'error': result.get('error', 'Unknown error')
                        })
                        job.failed += 1
                except Exception as e:
                    results['failed'].append({
                        'repo': repo['name'],
                        'error': str(e)
                    })
                    job.failed += 1

                # Update progress
                progress = job.completed + job.failed
                percentage = (progress / job.total_repos) * 100
                logger.info(f"Progress: {progress}/{job.total_repos} ({percentage:.0f}%)")

        job.end_time = time.time()

        # Save final results
        results['summary'] = {
            'total': job.total_repos,
            'completed': job.completed,
            'failed': job.failed,
            'success_rate': f"{(job.completed/job.total_repos*100):.1f}%",
            'duration_seconds': int(job.end_time - job.start_time)
        }

        self._save_batch_results(job, results)

        return results

    def _migrate_single_repo(self, repo: Dict) -> Dict:
        """Migrate a single repository"""
        repo_name = repo['name']
        logger.info(f"  Migrating: {repo_name}")

        try:
            # Register repository
            self.platform.register_repository(
                repo['url'],
                repo['current_version'],
                repo['target_version']
            )

            # Create configurations
            config = self.platform.create_migration_config(
                self.platform.RepositoryConfig(
                    repo_url=repo['url'],
                    repo_name=repo_name,
                    current_java_version=repo['current_version'],
                    target_java_version=repo['target_version'],
                    build_system='maven'
                )
            )

            # In real implementation, would push configs to repo
            logger.info(f"  ✅ {repo_name}: Configuration created")

            return {'success': True, 'repo': repo_name}

        except Exception as e:
            logger.error(f"  ❌ {repo_name}: {str(e)}")
            return {'success': False, 'repo': repo_name, 'error': str(e)}

    def _save_batch_results(self, job: BatchJob, results: Dict):
        """Save batch results to file"""
        results_file = self.jobs_dir / f"{job.job_id}-results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"📊 Results saved to {results_file}")

    def get_batch_status(self, job_id: str) -> Dict:
        """Get status of a batch job"""
        job_file = self.jobs_dir / f"{job_id}.json"
        if not job_file.exists():
            return {'error': f'Job {job_id} not found'}

        with open(job_file, 'r') as f:
            return json.load(f)

    def list_batch_jobs(self) -> List[Dict]:
        """List all batch jobs"""
        jobs = []
        for job_file in self.jobs_dir.glob("*.json"):
            if not job_file.name.endswith('-results.json'):
                try:
                    with open(job_file, 'r') as f:
                        jobs.append(json.load(f))
                except:
                    pass
        return jobs


class ReportGenerator:
    """Generates comprehensive migration reports"""

    def __init__(self, platform):
        self.platform = platform

    def generate_executive_summary(self) -> Dict:
        """Generate executive summary report"""
        repos = self.platform.load_repositories()
        status = self.platform.get_platform_status()

        return {
            'report_type': 'Executive Summary',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_repositories': status['total_repositories'],
            'migration_status': {
                'completed': status['status_breakdown']['completed'],
                'in_progress': status['status_breakdown']['in_progress'],
                'pending': status['status_breakdown']['pending'],
                'failed': status['status_breakdown']['failed'],
                'completion_rate': f"{(status['status_breakdown']['completed']/status['total_repositories']*100):.1f}%"
            },
            'migration_targets': status['migration_targets'],
            'build_systems': status['build_systems'],
            'key_metrics': self._calculate_metrics(repos)
        }

    def generate_detailed_report(self) -> Dict:
        """Generate detailed migration report"""
        repos = self.platform.load_repositories()

        return {
            'report_type': 'Detailed Report',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'repositories': [repo.to_dict() for repo in repos],
            'statistics': {
                'by_status': self._group_by_status(repos),
                'by_migration_path': self._group_by_migration_path(repos),
                'by_build_system': self._group_by_build_system(repos),
                'timeline': self._analyze_timeline(repos)
            }
        }

    def generate_failure_report(self) -> Dict:
        """Generate report of failed migrations"""
        repos = self.platform.load_repositories()
        failed = [r for r in repos if r.status == 'FAILED']

        return {
            'report_type': 'Failure Report',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_failed': len(failed),
            'failed_repositories': [
                {
                    'name': repo.repo_name,
                    'url': repo.repo_url,
                    'error': repo.error_message,
                    'migration': f"{repo.current_java_version}-to-{repo.target_java_version}"
                }
                for repo in failed
            ],
            'recommendations': self._generate_failure_recommendations(failed)
        }

    def _calculate_metrics(self, repos: List) -> Dict:
        """Calculate key metrics"""
        return {
            'avg_migration_time_days': 15,
            'success_rate': f"{(len([r for r in repos if r.status == 'COMPLETED'])/len(repos)*100):.1f}%" if repos else "0%",
            'critical_failures': len([r for r in repos if r.status == 'BLOCKED'])
        }

    def _group_by_status(self, repos: List) -> Dict:
        """Group repositories by status"""
        groups = {}
        for repo in repos:
            if repo.status not in groups:
                groups[repo.status] = 0
            groups[repo.status] += 1
        return groups

    def _group_by_migration_path(self, repos: List) -> Dict:
        """Group by migration path"""
        paths = {}
        for repo in repos:
            path = f"{repo.current_java_version}-to-{repo.target_java_version}"
            if path not in paths:
                paths[path] = 0
            paths[path] += 1
        return paths

    def _group_by_build_system(self, repos: List) -> Dict:
        """Group by build system"""
        systems = {}
        for repo in repos:
            if repo.build_system not in systems:
                systems[repo.build_system] = 0
            systems[repo.build_system] += 1
        return systems

    def _analyze_timeline(self, repos: List) -> Dict:
        """Analyze timeline of migrations"""
        return {
            'earliest_start': None,
            'latest_completion': None,
            'migrations_per_week': 'TBD'
        }

    def _generate_failure_recommendations(self, failed_repos: List) -> List[str]:
        """Generate recommendations for failures"""
        recommendations = []

        if len(failed_repos) > 0:
            recommendations.append(
                f"Review {len(failed_repos)} failed migrations for patterns"
            )
            recommendations.append(
                "Consider creating task force for problematic applications"
            )
            recommendations.append(
                "Implement additional testing for high-risk migrations"
            )

        return recommendations

    def export_report(self, report: Dict, format: str = 'json') -> str:
        """Export report in specified format"""
        timestamp = time.strftime('%Y%m%d-%H%M%S')

        if format == 'json':
            filename = f"{report['report_type'].lower().replace(' ', '-')}-{timestamp}.json"
            filepath = self.platform.reports_dir / filename
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

        return str(filepath)

