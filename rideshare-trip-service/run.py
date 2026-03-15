
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import init_database
from app import app
from config import Config

def main():
    """Initialize and run the Trip Service"""
    print("[Trip Service] Initializing Rideshare Trip Service...")
    
    try:
        # Initialize database
        print("[DB] Initializing database...")
        init_database()
        print("[OK] Database initialized successfully!")
        
        # Initialize background tasks
        from app import start_background_tasks
        start_background_tasks()
        
        # Start Flask application
        base_url = f"http://localhost:{Config.PORT}"
        print(f"[Network] Starting Trip Service on port {Config.PORT}...")
        print("")
        print("API Documentation (Swagger UI):")
        print(f"   - Swagger UI             -> {base_url}/api-docs/")
        print("")
        print("API Spec Files (JSON):")
        print(f"   - Frontend API spec      -> {base_url}/api-docs/frontend/apispec.json")
        print(f"   - Inter-Service API spec -> {base_url}/api-docs/inter-service/apispec.json")
        print(f"   - Combined API spec      -> {base_url}/api-docs/combined/apispec.json")
        print("")
        app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
        
    except Exception as e:
        print(f"[Error] Failed to start Trip Service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()