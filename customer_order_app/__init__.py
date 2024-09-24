from flask import Flask, redirect, url_for, session, request, jsonify, render_template
import os
import json
from .models import db, Customer, Order
from authlib.integrations.flask_client import OAuth
from flask_migrate import Migrate
from datetime import datetime

# Initialize OAuth and Migrate instances
oauth = OAuth()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Use PostgreSQL database URI from environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///customers_orders.db')
    
    # Debugging print (Optional: Remove in production)
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')  # Should be a strong random key in production

    # Define the path to the client secrets JSON file
    json_path = os.path.join(os.path.dirname(__file__), 'client_secrets.json')
    
    try:
        # Load client secrets securely
        with open(json_path) as f:
            secrets = json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"client_secrets.json not found at {json_path}")
    except json.JSONDecodeError:
        raise RuntimeError(f"Error decoding client_secrets.json at {json_path}")
    
    # Debugging print (Optional: Remove in production)
    print(f"Loaded secrets from: {json_path}")
    
    # Configure Auth0 settings
    auth0_config = secrets['web']
    app.config['AUTH0_CLIENT_ID'] = auth0_config['client_id']
    app.config['AUTH0_CLIENT_SECRET'] = auth0_config['client_secret']
    app.config['AUTH0_DOMAIN'] = auth0_config['issuer'].replace('https://', '').replace('/', '')
    app.config['AUTH0_CALLBACK_URL'] = auth0_config['redirect_uris'][0]

    # Initialize database and migration
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize OAuth and register Auth0
    oauth.init_app(app)
    oauth.register(
        'auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid profile email',
        },
        authorization_endpoint=auth0_config['auth_uri'],
        token_endpoint=auth0_config['token_uri'],
        issuer=auth0_config['issuer']
    )
    
    # Import and register the routes blueprint
    from .routes import main
    app.register_blueprint(main)
    
    return app
