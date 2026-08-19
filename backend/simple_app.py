#!/usr/bin/env python3
# simple_app.py - Simple Flask app for testing KPI calculations

from flask import Flask
from flask_cors import CORS
from routes.kpi_routes import kpi_bp

def create_app():
    """Simple application factory for testing KPI functionality."""
    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=['http://localhost:5173', 'http://localhost:3000'])

    # Register only the KPI blueprint
    app.register_blueprint(kpi_bp)

    # Simple home route
    @app.route("/")
    def home():
        return "Hercules KPI API - Test Version"

    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    print("Starting Hercules KPI API test server...")
    print("API will be available at: http://localhost:5000")
    print("KPI endpoint: http://localhost:5000/api/kpi")
    app.run(debug=True, host='0.0.0.0', port=5000)
