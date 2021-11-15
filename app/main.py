from flask import render_template, request, redirect, flash, url_for, session
from app import webapp
from app.config import S3_KEY, S3_SECRET, S3_BUCKET, S3_LOCATION
import os
import boto3


@webapp.route('/', methods=['GET', 'POST'])
def manager_login():
    if request.method == 'POST':
        session.pop('manager_name', None)
        input_managername = request.form['managername']
        input_password = request.form['password']

        if input_managername != 'manager':
            flash('Error password or managername', category='error')
            return render_template('main.html')
        else:
            if input_password == 'ece1779pass':
                session['manager_name'] = input_managername
                return redirect(url_for('manager_page'))
            else:
                flash('Error password or managername', category='error')
                return render_template('main.html', title='Login')
    else:
        return render_template('main.html', title='Login')


@webapp.route('/manager', methods=['GET', 'POST'])
def manager_page():
    os.environ['AWS_ACCESS_KEY_ID'] = S3_KEY
    os.environ['AWS_SECRET_ACCESS_KEY'] = S3_SECRET
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    #if 'manager_name' in session:
        #cloudwatch = boto3.client('cloudwatch')
    return render_template('manager/manager_page.html', title='Manager Page')


@webapp.route('/logout', methods=['GET', 'POST'])
def manager_logout():
    session.clear()
    return redirect(url_for('manager_login'))
