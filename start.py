"""
Quick start script for RAG system
Starts both API server and Streamlit UI
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def check_requirements():
    """Check if all required packages are installed"""
    print("Checking requirements...")
    try:
        import fastapi
        import streamlit
        import sentence_transformers
        import faiss
        print("✓ All required packages installed")
        return True
    except ImportError as e:
        print(f"✗ Missing package: {e.name}")
        print("\nPlease run: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        print("✗ .env file not found")
        print("\nPlease create .env file with:")
        print("OPENROUTER_API_KEY=your_api_key_here")
        return False
    print("✓ .env file found")
    return True

def check_data_files():
    """Check if data files exist"""
    data_dir = Path("data")
    required_files = ["index.faiss", "meta.json", "embeddings.npy"]
    
    missing = []
    for file in required_files:
        if not (data_dir / file).exists():
            missing.append(file)
    
    if missing:
        print(f"✗ Missing data files: {', '.join(missing)}")
        print("\nPlease run document ingestion first:")
        print("python src/ingest.py")
        return False
    
    print("✓ All data files present")
    return True

def start_api_server():
    """Start FastAPI server"""
    print("\n" + "="*60)
    print("Starting API Server...")
    print("="*60)
    
    api_process = subprocess.Popen(
        [sys.executable, "src/api_openrouter.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for server to start
    print("Waiting for API server to initialize...")
    time.sleep(10)
    
    return api_process

def start_streamlit():
    """Start Streamlit UI"""
    print("\n" + "="*60)
    print("Starting Streamlit UI...")
    print("="*60)
    
    # Check which frontend to use
    frontend_streamlit = Path("src/frontend_streamlit.py")
    frontend_v2 = Path("src/frontend_v2.py")
    frontend_enhanced = Path("src/frontend_enhanced.py")
    
    if frontend_streamlit.exists():
        frontend_file = "src/frontend_streamlit.py"
        print("Using UniSoftware Assistant Frontend")
    elif frontend_v2.exists():
        frontend_file = "src/frontend_v2.py"
        print("Using Enhanced Frontend V2")
    elif frontend_enhanced.exists():
        frontend_file = "src/frontend_enhanced.py"
        print("Using Standard Frontend")
    else:
        print("✗ No frontend file found!")
        sys.exit(1)
    
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", frontend_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return streamlit_process

def main():
    print("="*60)
    print("🚀 RAG System Startup")
    print("="*60)
    
    # Pre-flight checks
    if not check_requirements():
        sys.exit(1)
    
    if not check_env_file():
        sys.exit(1)
    
    if not check_data_files():
        sys.exit(1)
    
    print("\n✓ All checks passed!")
    
    # Start services
    try:
        api_process = start_api_server()
        streamlit_process = start_streamlit()
        
        print("\n" + "="*60)
        print("✅ RAG System Started Successfully!")
        print("="*60)
        print("\nAPI Server: http://localhost:8000")
        print("Streamlit UI: http://localhost:8501")
        print("\nPress Ctrl+C to stop both services")
        print("="*60)
        
        # Keep running
        try:
            api_process.wait()
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            api_process.terminate()
            streamlit_process.terminate()
            api_process.wait()
            streamlit_process.wait()
            print("✓ Services stopped")
            
    except Exception as e:
        print(f"\n✗ Error starting services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
