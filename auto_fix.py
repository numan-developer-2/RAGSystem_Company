"""
AUTO-FIX SCRIPT
Automatically resolves all detected issues
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def print_step(step, message):
    print(f"\n[{step}] {message}")
    print("="*70)

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def fix_missing_index():
    """Re-create FAISS index and metadata"""
    print_step("1/4", "Checking FAISS index...")
    
    index_path = Path("data/faiss_index.bin")
    metadata_path = Path("data/metadata.json")
    
    if not index_path.exists() or not metadata_path.exists():
        print("FAISS index or metadata missing. Running indexer...")
        
        success, stdout, stderr = run_command(
            "python src/indexer.py",
            cwd="D:/Python Project/RAG Project/rag-openrouter"
        )
        
        if success:
            print("[OK] Index created successfully!")
            return True
        else:
            print(f"[FAIL] Indexer failed: {stderr}")
            return False
    else:
        print("[OK] FAISS index exists")
        return True

def kill_port_8501():
    """Kill process on port 8501"""
    print_step("2/4", "Freeing port 8501...")
    
    success, stdout, stderr = run_command("netstat -ano | findstr :8501")
    
    if success and stdout.strip():
        print("Port 8501 in use. Killing process...")
        
        # Extract PID and kill
        lines = stdout.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                run_command(f"taskkill /F /PID {pid}")
        
        time.sleep(2)
        print("[OK] Port 8501 freed")
        return True
    else:
        print("[OK] Port 8501 already free")
        return True

def start_backend():
    """Start backend API server"""
    print_step("3/4", "Starting backend API...")
    
    # Check if already running
    success, stdout, stderr = run_command(
        "powershell -Command \"Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -TimeoutSec 2\""
    )
    
    if success:
        print("[OK] Backend already running")
        return True
    
    print("Starting backend server...")
    print("This will take 15-20 seconds for models to load...")
    
    # Start in background
    subprocess.Popen(
        ["python", "src/api_openrouter.py"],
        cwd="D:/Python Project/RAG Project/rag-openrouter",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    # Wait for server to start
    print("Waiting for backend to initialize...")
    for i in range(20):
        time.sleep(1)
        success, _, _ = run_command(
            "powershell -Command \"Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing -TimeoutSec 2\""
        )
        if success:
            print(f"[OK] Backend started successfully after {i+1} seconds!")
            return True
        print(f"  Waiting... ({i+1}/20)")
    
    print("[FAIL] Backend failed to start in 20 seconds")
    return False

def start_frontend():
    """Start frontend Streamlit"""
    print_step("4/4", "Starting frontend UI...")
    
    print("Launching Streamlit...")
    
    # Start in background
    subprocess.Popen(
        ["streamlit", "run", "src/frontend_streamlit.py"],
        cwd="D:/Python Project/RAG Project/rag-openrouter",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    print("Waiting for frontend to start...")
    time.sleep(8)
    
    # Open browser
    run_command("start http://localhost:8501")
    
    print("[OK] Frontend started!")
    return True

def main():
    """Main auto-fix routine"""
    print("\n" + "="*70)
    print("UNISOFTWARE ASSISTANT - AUTO-FIX SCRIPT")
    print("="*70)
    print("\nThis script will automatically:")
    print("  1. Re-create FAISS index if missing")
    print("  2. Free port 8501 if in use")
    print("  3. Start backend API server")
    print("  4. Start frontend Streamlit UI")
    print("\n" + "="*70)
    
    input("\nPress ENTER to continue...")
    
    results = []
    
    # Step 1: Fix missing index
    results.append(("Index Creation", fix_missing_index()))
    
    # Step 2: Free port 8501
    results.append(("Port 8501", kill_port_8501()))
    
    # Step 3: Start backend
    results.append(("Backend API", start_backend()))
    
    # Step 4: Start frontend
    results.append(("Frontend UI", start_frontend()))
    
    # Summary
    print("\n" + "="*70)
    print("AUTO-FIX SUMMARY")
    print("="*70)
    
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")
    
    if all(result[1] for result in results):
        print("\n[SUCCESS] All fixes applied successfully!")
        print("\nSystem is now running:")
        print("  Backend API: http://localhost:8000")
        print("  Frontend UI: http://localhost:8501")
        print("\nBrowser should open automatically.")
    else:
        print("\n[WARNING] Some fixes failed. Please review output above.")
        print("\nManual steps:")
        print("  1. Check terminal output for errors")
        print("  2. Run diagnostic: python diagnostic_report.py")
        print("  3. Contact support if issues persist")
    
    print("\n" + "="*70)
    input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()
