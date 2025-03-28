from flask import Blueprint
from .auth_routes import auth_bp
from .post_routes import post_bp
from .profile_routes import profile_bp
from .my_posts_routes import my_posts_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(post_bp, url_prefix="/api")
    app.register_blueprint(profile_bp, url_prefix="/api")
    app.register_blueprint(my_posts_bp, url_prefix="/api")
