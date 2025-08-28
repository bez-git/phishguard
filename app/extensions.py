from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"