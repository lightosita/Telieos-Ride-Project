from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flasgger import Swagger
from prometheus_client import generate_latest, REGISTRY
import logging
import os

from config import Config
from routes.trips import trips_bp       
from routes.fares import fares_bp
from routes.analytics import analytics_bp
from services.trip_service import TripService   
from events.event_handlers import start_event_listener
from swagger_config import swagger_config, swagger_template

# ========================
# Logging Configuration
# ========================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger('werkzeug').setLevel(logging.WARN)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ========================
# Automated Swagger Setup
# ========================
# Single Swagger instance with multiple spec files (one per audience).
# Flasgger only supports one blueprint per app; multiple instances break
# because the UI templates hardcode url_for('flasgger.static', ...).
swagger = Swagger(app, config=swagger_config, template=swagger_template)

# ========================
# CORS Configuration
# ========================
CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
            "supports_credentials": True
        }
    }
)

# ========================
# Register Blueprints
# ========================
app.register_blueprint(trips_bp, url_prefix='/api/v1/trips')       
app.register_blueprint(fares_bp, url_prefix='/api/v1/fares')
app.register_blueprint(analytics_bp, url_prefix='/api/v1/analytics')

# ========================
# Core Routes (Documented)
# ========================

@app.route('/')
def root():
    """
    Service Root
    ---
    responses:
      200:
        description: Returns service status and version
    """
    return jsonify({
        "message": "Trip & Fare Core Service is running",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/api-docs/"
    })

@app.route('/health')
def health_check():
    """
    Health Check
    ---
    responses:
      200:
        description: Service is healthy
    """
    return jsonify({"status": "healthy", "service": "trip-fare-core"})


# ========================
# Debug & Metrics
# ========================

@app.route('/test-db')
def test_db():
    """
    Database Connection Test
    ---
    responses:
      200:
        description: Database version info
    """
    try:
        from utils.database import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
        conn.close()
        return jsonify({"status": "connected", "postgresql_version": version})
    except Exception as e:
        logger.error(f"DB test failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    """
    Prometheus Metrics
    ---
    responses:
      200:
        description: Plaintext metrics for Prometheus
    """
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; version=0.0.4'}

# ========================
# Start Redis Listener
# ========================
def start_background_tasks():
    """Starts background processes like the Redis event listener."""
    logger.info("Starting Redis event listener in background...")
    try:
        start_event_listener()
        logger.info("Redis event listener STARTED successfully")
    except Exception as e:
        logger.critical(f"Failed to start Redis listener: {e}", exc_info=True)
        raise

# ========================
# Run App
# ========================
if __name__ == '__main__':
    # Initialize background tasks only when running directly
    start_background_tasks()
    
    os.makedirs('static', exist_ok=True)
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)