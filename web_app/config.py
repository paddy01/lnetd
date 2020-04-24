import os

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')
#SQLALCHEMY_DATABASE_URI = 'sqlite:////opt/lnetd/web_app/database.db')
#SECRET_KEY = 'secret_key_here'
SECRET_KEY = 'MyVeryS3cr3tK3y'
DEBUG = False
USER_ENABLE_EMAIL = False
USER_ENABLE_USERNAME = True
USER_REQUIRE_RETYPE_PASSWORD = False
SERVER_NAME = 'lnetd.xyz.ip-only.net'

INFLUXDB_HOST = '127.0.0.1'
INFLUXDB_PORT = '8806'
INFLUXDB_NAME = 'telegraf'
INFLUXDB_USERNAME = ''
INFLUXDB_PASSWORD = ''
