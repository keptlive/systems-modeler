#!/usr/bin/env python3
"""
Master test runner for Systems Modeler.
Runs all test suites and outputs a summary.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Change to project root
os.chdir(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_tests():
    """Run all test suites and return combined results."""
    print("=" * 60)
    print("SYSTEMS MODELER TEST SUITE")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    all_results = {}
    all_failures = []

    # Test 1: Models
    print("-" * 60)
    from tests.test_models import run_all_model_tests
    model_results = run_all_model_tests()
    all_results["Models"] = model_results
    for r in model_results["results"]:
        if not r["success"]:
            all_failures.append(("Model", r["name"], r["message"]))

    print()

    # Test 2: API
    print("-" * 60)
    from tests.test_api import run_all_api_tests
    api_results = run_all_api_tests()
    all_results["API"] = api_results
    for r in api_results["results"]:
        if not r["success"]:
            all_failures.append(("API", r["name"], r["message"]))

    print()

    # Test 3: Frontend
    print("-" * 60)
    from tests.test_frontend import run_all_frontend_tests
    frontend_results = run_all_frontend_tests()
    all_results["Frontend"] = frontend_results
    for r in frontend_results["results"]:
        if not r["success"]:
            all_failures.append(("Frontend", r["name"], r["message"]))

    print()

    # Summary
    print("=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    for category, results in all_results.items():
        status = "✓" if results["failed"] == 0 else "✗"
        print(f"{status} {category}: {results['passed']}/{results['total']} passing")
        total_passed += results["passed"]
        total_failed += results["failed"]

    print("-" * 60)
    print(f"TOTAL: {total_passed}/{total_passed + total_failed} passing")

    if all_failures:
        print()
        print("FAILURES:")
        for category, name, message in all_failures:
            print(f"  [{category}] {name}: {message}")

    print("=" * 60)

    return total_failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
