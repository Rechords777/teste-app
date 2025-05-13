import os
import sys
from dotenv import load_dotenv

# sys.path.insert(0, os.path.dirname(os.path.dirname(__file__))) # Commented out for flat structure, assuming main.py is in project root with other .py files
load_dotenv() # Looks for .env in current dir or parent dirs.

from flask import Flask, send_from_directory
from flask_cors import CORS
from extensions import db, migrate, socketio # Assuming extensions.py is in the same directory

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_default_secret_key_for_dev')
    # Ensure SQLALCHEMY_DATABASE_URI is set in .env or environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI') 
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        print("CRITICAL: SQLALCHEMY_DATABASE_URI is not set. Please set it in your .env file or environment variables.")
        # For local testing, you might want to default to SQLite if nothing is set:
        # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./default_local.db'
        # However, for Render, it must be configured via environment variables.

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db) # For Flask-Migrate
    CORS(app) # Enable CORS for all routes
    socketio.init_app(app, cors_allowed_origins="*") # Initialize SocketIO

    # Import blueprints after app and extensions are initialized
    from events import events_bp
    from metrics import metrics_bp
    from export import export_bp
    from logs import logs_bp

    app.register_blueprint(events_bp, url_prefix='/api')
    app.register_blueprint(metrics_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')
    app.register_blueprint(logs_bp, url_prefix='/api')

    # Route to serve static files (like a React frontend build) or a simple welcome message
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            # This case should ideally not happen if static_folder is always set
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                # If not an API route and no index.html, show a welcome message or a 404 for non-API paths.
                if not path.startswith('api/') and path != "favicon.ico": # ignore favicon requests for this message
                    return "Welcome to the Traffic Tracker API. No frontend UI is available at the root yet.", 200
                # For actual missing files or unhandled API-like paths that aren't blueprints
                return "Resource not found.", 404

    return app

app = create_app()

if __name__ == '__main__':
    # This block runs when script is executed directly (e.g., python main.py)
    # For production, Gunicorn is used as specified in Render's command.
    # The PORT environment variable is often set by hosting platforms like Render.
    port = int(os.getenv("PORT", 5000))
    print(f"Attempting to run SocketIO app on host 0.0.0.0, port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=True)

