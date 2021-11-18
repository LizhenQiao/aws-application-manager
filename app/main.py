from flask import render_template, request, redirect, flash, url_for, session
from app import webapp, config
from datetime import datetime, timedelta
from operator import itemgetter
from app.config import KEY, SECRET
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
    os.environ['AWS_ACCESS_KEY_ID'] = KEY
    os.environ['AWS_SECRET_ACCESS_KEY'] = SECRET
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    if 'manager_name' in session:
        client = boto3.client('cloudwatch')
        namespace = 'AWS/ApplicationELB'
        list_workers = client.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName='HealthyHostCount',
            Namespace=namespace,
            Statistics=['Average'],
            Dimensions=[{'Name': 'ImageId', 'Value': config.ami_id}]
        )
        list_workers_stat = []
        for point in list_workers['Datapoints']:
            hour = point['Timestamp'].hour
            minute = point['Timestamp'].minute
            time = hour + minute/60
            list_workers_stat.append([time, point['Average']])
        list_workers_stat = sorted(list_workers_stat, key=itemgetter(0))
    return render_template('manager/manager_page.html', title='Manager Page',
                           list_workers_stat=list_workers_stat)


@webapp.route('/logout', methods=['GET', 'POST'])
def manager_logout():
    session.clear()
    return redirect(url_for('manager_login'))
