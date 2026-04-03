import os
import sys
import subprocess
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("App")

def build_frontend():
    """Builds the frontend if the dist directory is missing."""
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    
    if not os.path.exists(dist_dir) or not os.path.exists(os.path.join(dist_dir, "index.html")):
        logger.info("Frontend build not found. Building frontend...")
        try:
            # Check if node_modules exists, if not install
            if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
                logger.info("Installing frontend dependencies...")
                subprocess.run("npm install", shell=True, cwd=frontend_dir, check=True)
            
            logger.info("Running npm build...")
            subprocess.run("npm run build", shell=True, cwd=frontend_dir, check=True)
            logger.info("Frontend built successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build frontend: {e}")
            sys.exit(1)
    else:
        logger.info("Frontend build found. Skipping build.")

def run_server():
    """Starts the Uvicorn server."""
    # Add backend directory to sys.path so 'rag_core' can be imported by main.py
    backend_dir = os.path.join(os.getcwd(), "backend")
    sys.path.append(backend_dir)
    
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting Backend Server at http://0.0.0.0:{port}")
    
    try:
        uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    print("===================================================")
    print("           Starting Mini RAG Application           ")
    print("===================================================")
    
    # 1. Ensure Frontend is built
    build_frontend()
    
    # 2. Run the Server
    run_server()
