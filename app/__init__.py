from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(SECRET_KEY="dev-change-me")
    if test_config:
        app.config.update(test_config)

    from .routes import bp
    app.register_blueprint(bp)
    from .transit_bca import bp as transit_bca_bp
    app.register_blueprint(transit_bca_bp)
    from .rail_forecast import bp as rail_forecast_bp
    app.register_blueprint(rail_forecast_bp)
    return app
