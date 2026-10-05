import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from astraflow_backend.api.routes import api_bp

def create_app():
    app = Flask(__name__)

    # Enable Cross-Origin Resource Sharing (CORS) for Angular frontend
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:4300", "*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return jsonify({
            "message": "Welcome to AstraFlow AI Traffic Intelligence API",
            "docs": "/api/health",
            "frontend": "http://localhost:4200"
        })

    return app

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚦 AstraFlow AI Backend & Traffic Intelligence Engine")
    print("="*60)
    print(" * Server listening at: http://127.0.0.1:5000")
    print(" * API Health check:   http://127.0.0.1:5000/api/health")
    print(" * Dashboard API:       http://127.0.0.1:5000/api/dashboard")
    print(" * Live Monitor API:    http://127.0.0.1:5000/api/live-monitor")
    print(" * Image Detection:     POST http://127.0.0.1:5000/api/detect/image")
    print(" * Angular UI Expected: http://localhost:4200")
    print("="*60 + "\n")

    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
