from __future__ import annotations

import time
import psutil
import threading
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .memory_store import MemoryStore
from .permissions import permission_manager
from .providers import provider_manager


class HealthMonitor:
    """Monitor system health and performance metrics"""

    def __init__(self):
        self.memory_store = MemoryStore()
        self.metrics_history: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.monitoring = False
        self.monitor_thread = None

        # Health thresholds
        self.thresholds = {
            "memory_usage_percent": 80.0,
            "cpu_usage_percent": 70.0,
            "response_time_ms": 5000,
            "error_rate_percent": 5.0,
            "db_size_mb": 100.0
        }

    def start_monitoring(self, interval_seconds: int = 60):
        """Start background health monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            "status": self._calculate_overall_health(),
            "timestamp": datetime.now().isoformat(),
            "system": self._get_system_metrics(),
            "application": self._get_application_metrics(),
            "alerts": self._get_recent_alerts(5),
            "uptime": self._get_uptime()
        }

    def _monitor_loop(self, interval: int):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)

                # Keep only last 24 hours of metrics
                cutoff = datetime.now() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m["timestamp"]) > cutoff
                ]

                # Check for alerts
                self._check_alerts(metrics)

                time.sleep(interval)
            except Exception as e:
                print(f"Health monitoring error: {e}")
                time.sleep(interval)

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system and application metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": self._get_system_metrics(),
            "application": self._get_application_metrics(),
            "database": self._get_database_metrics()
        }

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
            "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "network_connections": len(psutil.net_connections())
        }

    def _get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        provider_stats = provider_manager.get_usage_stats()
        permission_stats = permission_manager.get_permission_stats()

        return {
            "providers": provider_stats,
            "permissions": permission_stats,
            "memory_store": self.memory_store.get_stats()
        }

    def _get_database_metrics(self) -> Dict[str, Any]:
        """Get database-specific metrics"""
        try:
            import os
            db_path = self.memory_store.db_path
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
            else:
                db_size = 0

            return {
                "size_mb": db_size,
                "tables": self.memory_store.get_stats()
            }
        except Exception:
            return {"error": "Could not collect database metrics"}

    def _calculate_overall_health(self) -> str:
        """Calculate overall system health"""
        if not self.metrics_history:
            return "unknown"

        latest = self.metrics_history[-1]
        system = latest.get("system", {})

        # Critical thresholds
        if system.get("memory_percent", 0) > 95:
            return "critical"
        if system.get("cpu_percent", 0) > 90:
            return "critical"

        # Warning thresholds
        if (system.get("memory_percent", 0) > self.thresholds["memory_usage_percent"] or
            system.get("cpu_percent", 0) > self.thresholds["cpu_usage_percent"]):
            return "warning"

        return "healthy"

    def _check_alerts(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and create alerts"""
        system = metrics.get("system", {})

        # Memory usage alert
        if system.get("memory_percent", 0) > self.thresholds["memory_usage_percent"]:
            self._create_alert(
                "high_memory_usage",
                f"Memory usage is {system['memory_percent']:.1f}%",
                "warning"
            )

        # CPU usage alert
        if system.get("cpu_percent", 0) > self.thresholds["cpu_usage_percent"]:
            self._create_alert(
                "high_cpu_usage",
                f"CPU usage is {system['cpu_percent']:.1f}%",
                "warning"
            )

        # Database size alert
        db = metrics.get("database", {})
        if db.get("size_mb", 0) > self.thresholds["db_size_mb"]:
            self._create_alert(
                "large_database",
                f"Database size is {db['size_mb']:.1f}MB",
                "info"
            )

    def _create_alert(self, alert_type: str, message: str, severity: str):
        """Create a new alert"""
        alert = {
            "id": f"{alert_type}_{int(time.time())}",
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }

        self.alerts.append(alert)

        # Keep only recent alerts
        cutoff = datetime.now() - timedelta(hours=24)
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a["timestamp"]) > cutoff
        ]

    def _get_recent_alerts(self, count: int) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self.alerts[-count:] if self.alerts else []

    def _get_uptime(self) -> str:
        """Get system uptime (simplified)"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return str(timedelta(seconds=int(uptime_seconds)))
        except:
            # Fallback for non-Linux systems
            return "unknown"

    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics"""
        if not self.metrics_history:
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update health monitoring thresholds"""
        self.thresholds.update(new_thresholds)

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        if not self.metrics_history:
            return {"error": "No metrics history available"}

        # Analyze trends
        recent_metrics = self.get_metrics_history(1)  # Last hour

        if not recent_metrics:
            return {"error": "No recent metrics available"}

        # Calculate averages
        avg_memory = sum(m["system"]["memory_percent"] for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m["system"]["cpu_percent"] for m in recent_metrics) / len(recent_metrics)

        return {
            "period": "last_hour",
            "average_memory_percent": avg_memory,
            "average_cpu_percent": avg_cpu,
            "total_alerts": len(self.alerts),
            "health_status": self._calculate_overall_health(),
            "recommendations": self._generate_recommendations(avg_memory, avg_cpu)
        }

    def _generate_recommendations(self, avg_memory: float, avg_cpu: float) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        if avg_memory > 80:
            recommendations.append("Consider increasing system memory or optimizing memory usage")
        if avg_cpu > 70:
            recommendations.append("High CPU usage detected - consider optimizing performance")
        if len(self.alerts) > 10:
            recommendations.append("Frequent alerts detected - review system configuration")

        if not recommendations:
            recommendations.append("System performance is within normal parameters")

        return recommendations


# Global health monitor instance
health_monitor = HealthMonitor()