from app import webapp
from flask_mysqldb import MySQL
import yaml

# Configure db
db = yaml.load(open('app/static/db.yaml'), Loader=yaml.FullLoader)
webapp.config['MYSQL_HOST'] = db['mysql_host']
webapp.config['MYSQL_USER'] = db['mysql_user']
webapp.config['MYSQL_PASSWORD'] = db['mysql_password']
webapp.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(webapp)
