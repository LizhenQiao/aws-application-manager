from flask import Flask
import boto3
import config
import os
webapp = Flask(__name__)
webapp.secret_key = "you-will-never-know-lol"
webapp.jinja_env.auto_reload = True
webapp.config['TEMPLATES_AUTO_RELOAD'] = True
webapp.config['SESSION_TYPE'] = 'filesystem'

from app import main
from app import worker
from app import auto_scaler

