from flask import Flask
from routes.main import main_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from services.data_service import cache
from services.dash_app import init_dashboard_dash
import config


def create_app():
    app = Flask(__name__)
    app.config['CACHE_TYPE'] = config.CACHE_TYPE
    app.config['CACHE_DEFAULT_TIMEOUT'] = config.CACHE_DEFAULT_TIMEOUT

    cache.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    init_dashboard_dash(app)

    return app


# Module-level app instance for gunicorn (used by Render)
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
