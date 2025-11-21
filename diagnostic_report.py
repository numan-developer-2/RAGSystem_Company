"""
🔍 COMPREHENSIVE DIAGNOSTIC TOOL
Systematically diagnoses all project issues
"""
import sys
import os
import subprocess
import json
import socket
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_status(name, status, details=""):
    symbol = f"{Colors.GREEN}[OK]" if status else f"{Colors.RED}[FAIL]"
    print(f"{symbol}{Colors.RESET} {name}")
    if details:
        print(f"     {Colors.YELLOW}{details}{Colors.RESET}")

def check_python_version():
    """Check Python version compatibility"""
    print_header("1. PYTHON ENVIRONMENT")
    version = sys.version_info
    is_compatible = version.major == 3 and version.minor >= 8
    print_status(
        "Python Version",
        is_compatible,
        f"Python {version.major}.{version.minor}.{version.micro} (Required: 3.8+)"
    )
    return is_compatible

def check_dependencies():
    """Check if all required packages are installed"""
    print_header("2. DEPENDENCY VALIDATION")
    
    required_packages = {
        'streamlit': 'streamlit',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'sentence_transformers': 'sentence-transformers',
        'faiss': 'faiss-cpu',
        'requests': 'requests',
        'openai': 'openai',
    }
    
    all_installed = True
    for module, package in required_packages.items():
        try:
            __import__(module)
            print_status(f"{package}", True, "Installed")
        except ImportError:
            print_status(f"{package}", False, "NOT INSTALLED")
            all_installed = False
    
    return all_installed

def check_project_structure():
    """Validate project directory structure"""
    print_header("3. PROJECT STRUCTURE")
    
    base_dir = Path("D:/Python Project/RAG Project/rag-openrouter")
    required_files = [
        "src/api_openrouter.py",
        "src/frontend_streamlit.py",
        "src/rag_engine.py",
        "data/faiss_index.bin",
        "data/metadata.json",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = base_dir / file_path
        exists = full_path.exists()
        print_status(
            file_path,
            exists,
            f"Size: {full_path.stat().st_size if exists else 0} bytes"
        )
        if not exists:
            all_exist = False
    
    return all_exist

def check_ports():
    """Check if required ports are available"""
    print_header("4. PORT AVAILABILITY")
    
    ports = {8000: "Backend API", 8501: "Frontend UI"}
    all_free = True
    
    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print_status(f"Port {port} ({service})", False, "IN USE")
            all_free = False
        else:
            print_status(f"Port {port} ({service})", True, "AVAILABLE")
    
    return all_free

def check_api_server():
    """Check if backend API is running"""
    print_header("5. BACKEND API STATUS")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("API Server", True, "RUNNING")
            print_status("Documents", True, f"{data.get('documents', 0)} loaded")
            print_status("Chunks", True, f"{data.get('total_chunks', 0)} indexed")
            return True
        else:
            print_status("API Server", False, f"HTTP {response.status_code}")
            return False
    except Exception as e:
        print_status("API Server", False, f"NOT RUNNING - {str(e)}")
        return False

def check_environment_variables():
    """Check required environment variables"""
    print_header("6. ENVIRONMENT CONFIGURATION")
    
    env_vars = {
        'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY'),
    }
    
    all_set = True
    for var, value in env_vars.items():
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print_status(var, True, f"Set: {masked}")
        else:
            print_status(var, False, "NOT SET")
            all_set = False
    
    return all_set

def generate_recommendations(results):
    """Generate actionable recommendations"""
    print_header("7. DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    
    issues = []
    
    if not results['python']:
        issues.append("[X] Python version incompatible. Install Python 3.8+")
    
    if not results['dependencies']:
        issues.append("[X] Missing dependencies. Run: pip install -r requirements.txt")
    
    if not results['structure']:
        issues.append("[X] Missing project files. Re-run indexer: python src/indexer.py")
    
    if not results['ports']:
        issues.append("[!] Ports in use. Kill processes: netstat -ano | findstr :8000")
    
    if not results['api']:
        issues.append("[X] Backend API not running. Start: python src/api_openrouter.py")
    
    if not results['env']:
        issues.append("[!] Environment variables not set. Check .env file")
    
    if issues:
        print(f"{Colors.RED}ISSUES FOUND:{Colors.RESET}")
        for issue in issues:
            print(f"  {issue}")
        print(f"\n{Colors.YELLOW}RECOMMENDED FIX:{Colors.RESET}")
        print(f"  1. Install dependencies: pip install -r requirements.txt")
        print(f"  2. Start backend: python src/api_openrouter.py")
        print(f"  3. Wait 15 seconds for models to load")
        print(f"  4. Start frontend: streamlit run src/frontend_streamlit.py")
    else:
        print(f"{Colors.GREEN}ALL CHECKS PASSED!{Colors.RESET}")
        print(f"  System is ready to run.")

def main():
    """Run comprehensive diagnostics"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}UNISOFTWARE ASSISTANT - COMPREHENSIVE DIAGNOSTICS{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}")
    
    results = {
        'python': check_python_version(),
        'dependencies': check_dependencies(),
        'structure': check_project_structure(),
        'ports': check_ports(),
        'api': check_api_server(),
        'env': check_environment_variables(),
    }
    
    generate_recommendations(results)
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}Diagnostic complete. Review recommendations above.{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
    # Return exit code
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    exit(main())
