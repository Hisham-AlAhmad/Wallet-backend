# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    # Import and register routes
    from app.routes.auth import init_auth_routes
    from app.routes.wallet import init_wallet_routes

    init_auth_routes(app)
    init_wallet_routes(app)

    return app
