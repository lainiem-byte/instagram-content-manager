import subprocess
import os
import sys
import time

def start_backend():
    print("Starting FastAPI Backend on http://localhost:8000...")
    return subprocess.Popen([sys.executable, "-m", "uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"])

def start_frontend():
    print("Starting Next.js Frontend on http://localhost:3000...")
    os.chdir("frontend")
    # Using shell=True for npm on Windows
    return subprocess.Popen("npm run dev", shell=True)

if __name__ == "__main__":
    backend_proc = start_backend()
    time.sleep(2) # Give backend a moment
    frontend_proc = start_frontend()

    print("\n" + "="*50)
    print("INSTAGRAM AGENT WEB APP IS RUNNING")
    print("Dashboard: http://localhost:3000")
    print("API Documentation: http://localhost:8000/docs")
    print("="*50 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping processes...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("Done.")
