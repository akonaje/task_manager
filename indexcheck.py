from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'http://127.0.0.1:5000'  # Replace with your actual database URI
db = SQLAlchemy(app)
migrate = Migrate(app, db)
