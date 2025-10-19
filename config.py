import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-key-please-change'
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'phishguard.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', True)

    # Model paths and settings
    PHISH_MODEL_PATH = os.environ.get('PHISH_MODEL_PATH')
    PHISH_IMPUTER_PATH = os.environ.get('PHISH_IMPUTER_PATH')
    PHISH_FEATURE_ORDER_PATH = os.environ.get('PHISH_FEATURE_ORDER_PATH')
    PHISH_TLD_FREQ_PATH = os.environ.get('PHISH_TLD_FREQ_PATH')
    PHISH_THRESHOLD_PATH = os.environ.get('PHISH_THRESHOLD_PATH')
    PHISH_THRESHOLD = float(os.environ.get('PHISH_THRESHOLD', 0.90))
    PHISH_NAN_DEFAULT = float(os.environ.get('PHISH_NAN_DEFAULT', 0.5))