#!/usr/bin/env python3
"""
Real-time Memory Monitor for Production
Monitors gunicorn worker memory usage and flags potential leaks.
"""

import time
import psutil
import subprocess
import argparse
from datetime import datetime


def find_gunicorn_workers():
    """Find all gunicorn worker processes"""
    workers = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'gunicorn' in proc.info['name']:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'worker' in cmdline or 'django_config.wsgi' in cmdline:
                    workers.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return workers


def get_memory_stats(proc):
    """Get memory statistics for a process"""
    try:
        mem_info = proc.memory_info()
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'pid': proc.pid,
            'create_time': proc.create_time()
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def format_uptime(create_time):
    """Format process uptime"""
    uptime_seconds = time.time() - create_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    return f"{hours}h{minutes}m"


def monitor_workers(interval=10, threshold_mb=500):
    """
    Monitor gunicorn workers for memory leaks

    Args:
        interval: Monitoring interval in seconds
        threshold_mb: Memory threshold to flag as potential leak
    """
    print("=" * 80)
    print("GUNICORN WORKER MEMORY MONITOR")
    print(f"Monitoring interval: {interval}s | Leak threshold: {threshold_mb}MB")
    print("=" * 80)

    worker_baselines = {}

    try:
        while True:
            workers = find_gunicorn_workers()

            if not workers:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No gunicorn workers found. Waiting...")
                time.sleep(interval)
                continue

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Workers: {len(workers)}")
            print("-" * 80)
            print(f"{'PID':>8} {'RSS (MB)':>12} {'VMS (MB)':>12} {'Δ RSS':>10} {'Uptime':>10} {'Status'}")
            print("-" * 80)

            for worker in workers:
                stats = get_memory_stats(worker)
                if not stats:
                    continue

                pid = stats['pid']
                rss_mb = stats['rss_mb']
                vms_mb = stats['vms_mb']
                uptime = format_uptime(stats['create_time'])

                # Track baseline and delta
                if pid not in worker_baselines:
                    worker_baselines[pid] = rss_mb
                    delta_rss = 0.0
                    status = "NEW"
                else:
                    delta_rss = rss_mb - worker_baselines[pid]

                    if rss_mb > threshold_mb:
                        status = "LEAK"
                    elif delta_rss > threshold_mb * 0.3:
                        status = "WARNING"
                    else:
                        status = "OK"

                print(f"{pid:>8} {rss_mb:>11.1f} {vms_mb:>11.1f} {delta_rss:>+9.1f} {uptime:>10} {status}")

            # Clean up baselines for dead workers
            current_pids = {w.pid for w in workers}
            dead_pids = set(worker_baselines.keys()) - current_pids
            for pid in dead_pids:
                del worker_baselines[pid]

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor gunicorn worker memory usage")
    parser.add_argument('-i', '--interval', type=int, default=10,
                        help='Monitoring interval in seconds (default: 10)')
    parser.add_argument('-t', '--threshold', type=int, default=500,
                        help='Memory leak threshold in MB (default: 500)')

    args = parser.parse_args()
    monitor_workers(interval=args.interval, threshold_mb=args.threshold)
