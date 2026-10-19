"""
Observability Metrics Registry for Research Intelligence Assistant V2.
Records genuine operational measurements without simulated numbers or fake telemetry.
"""

import threading
import time
from collections import defaultdict
from typing import Any, Dict


class ObservabilityRegistry:
    """Thread-safe in-process metrics registry."""

    def __init__(self):
        self._lock = threading.Lock()
        self.api_requests_total = defaultdict(int)
        self.api_request_durations = []  # Recent request latencies in seconds
        self.research_jobs_total = defaultdict(int)
        self.research_job_durations = []  # Recent job runtimes in seconds
        self.provider_failures_total = defaultdict(int)
        self.database_failures_total = 0
        self.loop_termination_reasons_total = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
        """Records an HTTP request completion."""
        with self._lock:
            key = f"{method}:{endpoint}:{status_code}"
            self.api_requests_total[key] += 1
            self.api_request_durations.append(duration_seconds)
            if len(self.api_request_durations) > 1000:
                self.api_request_durations.pop(0)

    def record_job_lifecycle(self, status: str, duration_seconds: float = 0.0) -> None:
        """Records a research job state transition."""
        with self._lock:
            self.research_jobs_total[status] += 1
            if duration_seconds > 0:
                self.research_job_durations.append(duration_seconds)
                if len(self.research_job_durations) > 1000:
                    self.research_job_durations.pop(0)

    def record_provider_failure(self, provider: str, error_type: str) -> None:
        """Records an external search provider failure."""
        with self._lock:
            self.provider_failures_total[f"{provider}:{error_type}"] += 1

    def record_database_failure(self) -> None:
        """Records a database persistence failure."""
        with self._lock:
            self.database_failures_total += 1

    def record_loop_termination(self, reason: str) -> None:
        """Records a Stage 5 research loop termination reason."""
        with self._lock:
            self.loop_termination_reasons_total[reason] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Returns JSON-serializable structured observability telemetry."""
        with self._lock:
            durations = self.api_request_durations
            avg_api_duration = sum(durations) / len(durations) if durations else 0.0
            p95_api_duration = sorted(durations)[int(len(durations) * 0.95)] if durations else 0.0

            job_durations = self.research_job_durations
            avg_job_duration = sum(job_durations) / len(job_durations) if job_durations else 0.0

            return {
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "api": {
                    "total_requests": sum(self.api_requests_total.values()),
                    "by_route": dict(self.api_requests_total),
                    "avg_duration_seconds": round(avg_api_duration, 4),
                    "p95_duration_seconds": round(p95_api_duration, 4)
                },
                "research_jobs": {
                    "by_status": dict(self.research_jobs_total),
                    "avg_duration_seconds": round(avg_job_duration, 2)
                },
                "failures": {
                    "providers": dict(self.provider_failures_total),
                    "database": self.database_failures_total
                },
                "loop_termination_reasons": dict(self.loop_termination_reasons_total)
            }

    def to_prometheus_format(self) -> str:
        """Formats real recorded metrics in Prometheus text exposition format."""
        lines = []
        with self._lock:
            lines.append("# HELP api_requests_total Total number of API requests handled")
            lines.append("# TYPE api_requests_total counter")
            for key, count in self.api_requests_total.items():
                parts = key.split(":")
                if len(parts) == 3:
                    method, path, status = parts
                    lines.append(f'api_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            lines.append("# HELP research_jobs_total Total research jobs processed by state")
            lines.append("# TYPE research_jobs_total counter")
            for status, count in self.research_jobs_total.items():
                lines.append(f'research_jobs_total{{status="{status}"}} {count}')

            lines.append("# HELP provider_failures_total Failures encountered calling search providers")
            lines.append("# TYPE provider_failures_total counter")
            for prov_err, count in self.provider_failures_total.items():
                parts = prov_err.split(":")
                if len(parts) == 2:
                    p, e = parts
                    lines.append(f'provider_failures_total{{provider="{p}",error="{e}"}} {count}')

            lines.append(f"database_failures_total {self.database_failures_total}")
            lines.append(f"system_uptime_seconds {round(time.time() - self.start_time, 2)}")

        return "\n".join(lines) + "\n"


# Global metrics singleton
metrics = ObservabilityRegistry()
