"""Resource monitoring utilities for tracking memory leaks and resource usage."""

import os
import psutil
import subprocess
import asyncio
import logging
from typing import Dict, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class ResourceSnapshot:
    """Snapshot of current resource usage."""

    def __init__(self):
        self.pid = os.getpid()
        self.memory_mb = self._get_memory_mb()
        self.open_fds = self._get_open_fds()
        self.asyncio_tasks = self._get_asyncio_task_count()
        self.browser_processes = self._get_browser_process_count()

    def _get_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            process = psutil.Process(self.pid)
            return process.memory_info().rss / 1024 / 1024
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {e}")
            return 0.0

    def _get_open_fds(self) -> int:
        """Get count of open file descriptors."""
        try:
            process = psutil.Process(self.pid)
            return process.num_fds()
        except Exception:
            return 0

    def _get_asyncio_task_count(self) -> int:
        """Get count of running asyncio tasks."""
        try:
            loop = asyncio.get_event_loop()
            tasks = asyncio.all_tasks(loop)
            return len(tasks)
        except Exception:
            return 0

    def _get_browser_process_count(self) -> int:
        """Get count of Chrome/Chromium browser processes."""
        try:
            result = subprocess.run(
                ['pgrep', '-c', 'chrome|chromium'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0

    def delta(self, previous: 'ResourceSnapshot') -> Dict[str, float]:
        """Calculate resource delta from previous snapshot."""
        return {
            'memory_delta_mb': round(self.memory_mb - previous.memory_mb, 2),
            'fd_delta': self.open_fds - previous.open_fds,
            'task_delta': self.asyncio_tasks - previous.asyncio_tasks,
            'browser_delta': self.browser_processes - previous.browser_processes,
        }

    def to_dict(self) -> Dict[str, any]:
        """Convert snapshot to dictionary."""
        return {
            'pid': self.pid,
            'memory_mb': round(self.memory_mb, 2),
            'open_fds': self.open_fds,
            'asyncio_tasks': self.asyncio_tasks,
            'browser_processes': self.browser_processes,
        }


def get_mcp_connection_count() -> int:
    """
    Get count of active MCP connections.

    This requires accessing the global MCP manager if available.
    """
    try:
        from mcp_client.apps import get_global_mcp_manager
        manager = get_global_mcp_manager()
        if manager and hasattr(manager, 'clients'):
            return len(manager.clients)
    except Exception as e:
        logger.debug(f"Could not get MCP connection count: {e}")
    return 0


def track_resources(func):
    """
    Decorator to track resource usage for a function.

    Logs resource deltas before/after function execution.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        before = ResourceSnapshot()
        try:
            return await func(*args, **kwargs)
        finally:
            after = ResourceSnapshot()
            delta = after.delta(before)
            if delta['memory_delta_mb'] > 5:
                logger.warning(
                    f"{func.__name__} memory_delta={delta['memory_delta_mb']}MB "
                    f"fd_delta={delta['fd_delta']} task_delta={delta['task_delta']}"
                )

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        before = ResourceSnapshot()
        try:
            return func(*args, **kwargs)
        finally:
            after = ResourceSnapshot()
            delta = after.delta(before)
            if delta['memory_delta_mb'] > 5:
                logger.warning(
                    f"{func.__name__} memory_delta={delta['memory_delta_mb']}MB "
                    f"fd_delta={delta['fd_delta']} task_delta={delta['task_delta']}"
                )

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
