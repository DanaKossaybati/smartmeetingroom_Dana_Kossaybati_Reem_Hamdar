#!/usr/bin/env python3
"""
Performance, Memory, and Code Coverage Profiling Script for Users Service
Generates profiling reports with coverage metrics and performance analysis

Author: Dana Kossaybati
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

CURRENT_DIR = Path(__file__).parent
REPORT_DIR = CURRENT_DIR.parent.parent / "profiling_reports"

# Create report directory
REPORT_DIR.mkdir(exist_ok=True)

def run_command(cmd, cwd=None, timeout=120):
    """Run a shell command and return output"""
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed_time = time.time() - start_time
        return result.stdout + result.stderr, result.returncode, elapsed_time
    except subprocess.TimeoutExpired:
        return "Command timed out", 1, timeout
    except Exception as e:
        return str(e), 1, 0

def analyze_coverage():
    """Analyze code coverage for users service"""
    print("\n" + "="*70)
    print("USERS SERVICE - CODE COVERAGE ANALYSIS")
    print("="*70 + "\n")
    
    # Run tests with coverage
    print("Running tests with coverage analysis...")
    cmd = (
        "python -m pytest tests/ "
        "--cov=. --cov-report=json --cov-report=html "
        "--cov-report=term-missing -q --tb=short"
    )
    output, returncode, elapsed_time = run_command(cmd, cwd=CURRENT_DIR)
    
    coverage_data = {
        "timestamp": datetime.now().isoformat(),
        "test_execution_time": elapsed_time,
        "test_status": "PASSED" if returncode == 0 else "FAILED",
        "files": {}
    }
    
    # Parse coverage.json if it exists
    coverage_json_path = CURRENT_DIR / "coverage.json"
    if coverage_json_path.exists():
        try:
            with open(coverage_json_path) as f:
                cov_json = json.load(f)
                totals = cov_json.get("totals", {})
                
                coverage_data["total_coverage_percent"] = totals.get("percent_covered", 0)
                coverage_data["total_lines"] = totals.get("num_statements", 0)
                coverage_data["covered_lines"] = totals.get("covered_lines", 0)
                coverage_data["missing_lines"] = totals.get("num_statements", 0) - totals.get("covered_lines", 0)
                
                # Analyze individual files
                for file_path, file_data in cov_json.get("files", {}).items():
                    file_name = Path(file_path).name
                    if file_name.endswith(".py") and not file_name.startswith("test_"):
                        summary = file_data.get("summary", {})
                        coverage_data["files"][file_name] = {
                            "coverage": summary.get("percent_covered", 0),
                            "lines": summary.get("num_statements", 0),
                            "covered": summary.get("covered_lines", 0),
                            "missing": summary.get("num_statements", 0) - summary.get("covered_lines", 0)
                        }
        except Exception as e:
            print(f"Error parsing coverage.json: {e}")
    
    print(f"\nTest Execution Time: {elapsed_time:.2f}s")
    print(f"Test Status: {coverage_data['test_status']}")
    print(f"\nCoverage Summary:")
    print(f"  Total Coverage: {coverage_data.get('total_coverage_percent', 0):.1f}%")
    print(f"  Total Lines: {coverage_data.get('total_lines', 0)}")
    print(f"  Covered Lines: {coverage_data.get('covered_lines', 0)}")
    print(f"  Missing Lines: {coverage_data.get('missing_lines', 0)}")
    
    print(f"\nPer-File Coverage:")
    for file_name, file_stats in sorted(coverage_data["files"].items()):
        print(f"  {file_name}:")
        print(f"    - Coverage: {file_stats['coverage']:.1f}%")
        print(f"    - Lines: {file_stats['lines']} (Covered: {file_stats['covered']}, Missing: {file_stats['missing']})")
    
    return coverage_data

def analyze_performance():
    """Analyze performance metrics"""
    print("\n" + "="*70)
    print("USERS SERVICE - PERFORMANCE METRICS")
    print("="*70 + "\n")
    
    perf_data = {
        "timestamp": datetime.now().isoformat(),
        "code_metrics": {},
        "test_metrics": {}
    }
    
    # Count lines of code
    print("Analyzing code metrics...")
    py_files = []
    total_loc = 0
    total_functions = 0
    total_classes = 0
    
    for py_file in CURRENT_DIR.glob("*.py"):
        if py_file.is_file() and not py_file.name.startswith("test_"):
            with open(py_file) as f:
                content = f.read()
                lines = content.split('\n')
                loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
                funcs = content.count('def ')
                classes = content.count('class ')
                
                py_files.append({
                    "name": py_file.name,
                    "loc": loc,
                    "functions": funcs,
                    "classes": classes
                })
                total_loc += loc
                total_functions += funcs
                total_classes += classes
    
    perf_data["code_metrics"]["files"] = py_files
    perf_data["code_metrics"]["total_loc"] = total_loc
    perf_data["code_metrics"]["total_functions"] = total_functions
    perf_data["code_metrics"]["total_classes"] = total_classes
    
    print(f"\nCode Metrics:")
    print(f"  Total Lines of Code: {total_loc}")
    print(f"  Total Functions: {total_functions}")
    print(f"  Total Classes: {total_classes}")
    print(f"  Number of Modules: {len(py_files)}")
    
    print(f"\nPer-Module Breakdown:")
    for file_info in sorted(py_files, key=lambda x: x['loc'], reverse=True):
        print(f"  {file_info['name']}:")
        print(f"    - LOC: {file_info['loc']}")
        print(f"    - Functions: {file_info['functions']}")
        print(f"    - Classes: {file_info['classes']}")
    
    # Run tests to measure execution time
    print("\n\nMeasuring test execution times...")
    
    # Check what test files exist
    test_dir = CURRENT_DIR / "tests"
    test_files = list(test_dir.glob("test_*.py")) if test_dir.exists() else []
    
    if test_files:
        # Run all tests
        cmd = "python -m pytest tests/ -v --tb=short"
        output, _, total_time = run_command(cmd, cwd=CURRENT_DIR)
        perf_data["test_metrics"]["total_tests_time"] = total_time
        print(f"\nTest Execution Times:")
        print(f"  All Tests: {total_time:.2f}s")
    else:
        print("\nNo test files found")
        perf_data["test_metrics"]["total_tests_time"] = 0
    
    return perf_data

def generate_report(coverage_data, perf_data):
    """Generate comprehensive profiling report"""
    print("\n" + "="*70)
    print("GENERATING PROFILING REPORT")
    print("="*70 + "\n")
    
    report = {
        "service": "users",
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage_data,
        "performance": perf_data
    }
    
    # Save JSON report
    report_file = REPORT_DIR / f"users_profiling_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"JSON Report saved to: {report_file}")
    
    # Generate text summary report
    summary_file = REPORT_DIR / f"users_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(summary_file, "w") as f:
        f.write("USERS SERVICE PROFILING REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Author: Dana Kossaybati\n\n")
        
        f.write("COVERAGE METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Coverage: {coverage_data.get('total_coverage_percent', 0):.1f}%\n")
        f.write(f"Total Lines: {coverage_data.get('total_lines', 0)}\n")
        f.write(f"Covered Lines: {coverage_data.get('covered_lines', 0)}\n")
        f.write(f"Missing Lines: {coverage_data.get('missing_lines', 0)}\n")
        f.write(f"Test Status: {coverage_data.get('test_status', 'UNKNOWN')}\n")
        f.write(f"Test Execution Time: {coverage_data.get('test_execution_time', 0):.2f}s\n\n")
        
        f.write("CODE METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Lines of Code: {perf_data['code_metrics']['total_loc']}\n")
        f.write(f"Total Functions: {perf_data['code_metrics']['total_functions']}\n")
        f.write(f"Total Classes: {perf_data['code_metrics']['total_classes']}\n")
        f.write(f"Number of Modules: {len(perf_data['code_metrics']['files'])}\n\n")
        
        f.write("TEST PERFORMANCE\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Test Execution Time: {perf_data['test_metrics'].get('total_tests_time', 0):.2f}s\n")
    
    print(f"Summary Report saved to: {summary_file}")
    
    return report

def main():
    """Main profiling function"""
    print("\n" + "="*70)
    print("USERS SERVICE PROFILING SUITE")
    print("="*70)
    print(f"Author: Dana Kossaybati")
    print(f"Started: {datetime.now().isoformat()}\n")
    
    try:
        # Run analyses
        coverage_data = analyze_coverage()
        perf_data = analyze_performance()
        
        # Generate report
        report = generate_report(coverage_data, perf_data)
        
        print("\n" + "="*70)
        print("PROFILING COMPLETE")
        print("="*70)
        print(f"Ended: {datetime.now().isoformat()}\n")
        
        return report
    except Exception as e:
        print(f"\nError during profiling: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
