"""
Test runner script
Run all tests and generate report
"""
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Running RAG System Tests")
    print("=" * 60)
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"])
    
    # Run unit tests
    print("\n📦 Running Unit Tests...")
    result_unit = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_unit.py", "-v"],
        capture_output=False
    )
    
    # Run integration tests
    print("\n🔗 Running Integration Tests...")
    print("⚠️  Make sure API server is running on http://localhost:8000")
    input("Press Enter to continue...")
    
    result_integration = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_integration.py", "-v"],
        capture_output=False
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"Unit Tests: {'✅ PASSED' if result_unit.returncode == 0 else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if result_integration.returncode == 0 else '❌ FAILED'}")
    print("=" * 60)
    
    return result_unit.returncode == 0 and result_integration.returncode == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
