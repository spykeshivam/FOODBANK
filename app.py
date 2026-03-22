from flask import Flask
# Import the blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from services.data_service import cache
from services.dash_app import init_dashboard_dash
import config # Import config here as well

def create_app():
    app = Flask(__name__)

    # BEST PRACTICE: Load config from config.py
    app.config['CACHE_TYPE'] = config.CACHE_TYPE
    app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_DEFAULT_TIMEOUT
    
    cache.init_app(app)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    init_dashboard_dash(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0")
