#!/usr/bin/env python3
"""
Enhanced Profiling Script: Performance, Memory, and Code Coverage
Author: Dana Kossaybati
"""

import subprocess
import json
import psutil
import os
from pathlib import Path
from datetime import datetime
import time

CURRENT_DIR = Path(__file__).parent
REPORT_DIR = CURRENT_DIR / "profiling_reports"
REPORT_DIR.mkdir(exist_ok=True)

def get_memory_usage():
    """Get current process memory usage"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def run_pytest_with_memory():
    """Run pytest and capture memory metrics"""
    print("\n" + "="*70)
    print("USERS SERVICE - PERFORMANCE, MEMORY & CODE COVERAGE")
    print("="*70 + "\n")
    
    print("[1] MEMORY PROFILING")
    print("-" * 70)
    
    start_mem = get_memory_usage()
    print(f"Starting Memory: {start_mem:.2f} MB")
    
    start_time = time.time()
    
    # Run tests with coverage
    cmd = "python -m pytest tests/ --cov=. --cov-report=json --cov-report=term-missing -q"
    result = subprocess.run(cmd, shell=True, cwd=str(CURRENT_DIR), capture_output=True, text=True)
    
    elapsed_time = time.time() - start_time
    end_mem = get_memory_usage()
    peak_mem = end_mem
    
    print(f"Ending Memory: {end_mem:.2f} MB")
    print(f"Memory Used: {end_mem - start_mem:.2f} MB")
    print(f"Execution Time: {elapsed_time:.2f} seconds")
    
    print("\n[2] TEST RESULTS")
    print("-" * 70)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print("\n[3] CODE COVERAGE REPORT")
    print("-" * 70)
    
    # Read coverage JSON
    coverage_file = CURRENT_DIR / ".coverage"
    if coverage_file.exists():
        # Run coverage report
        cov_cmd = "python -m coverage report"
        cov_result = subprocess.run(cov_cmd, shell=True, cwd=str(CURRENT_DIR), capture_output=True, text=True)
        print(cov_result.stdout)
    
    return {
        "service": "users",
        "timestamp": datetime.now().isoformat(),
        "memory": {
            "start_mb": round(start_mem, 2),
            "end_mb": round(end_mem, 2),
            "used_mb": round(end_mem - start_mem, 2),
            "peak_mb": round(peak_mem, 2)
        },
        "performance": {
            "execution_time_seconds": round(elapsed_time, 2),
            "tests_passed": "Yes" if result.returncode == 0 else "No"
        }
    }

if __name__ == "__main__":
    data = run_pytest_with_memory()
    
    # Save report
    report_file = REPORT_DIR / f"users_profiling_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\n" + "="*70)
    print(f"Report saved to: {report_file}")
    print("="*70)
