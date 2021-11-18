from flask import render_template, request, redirect, flash, url_for, session
from app import webapp, config
from datetime import datetime, timedelta
from operator import itemgetter
from app.config import KEY, SECRET, S3_BUCKET
from .MySQL_DB import mysql
import os
import boto3

filters = [
    {
        "Name": "instance-state-name",
        'Values': ['running', 'pending']
    },
    {
        "Name": "image-id",
        "Values": [config.ami_id]
    }
]

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


@webapp.route('/stop', methods=['GET'])
def stop_manager_app():
    worker_count = 0
    ec2 = boto3.resource("ec2")
    instances = ec2.instances.filter(Filters=filter)
    running_instances = []
    for instance in instances:
        worker_count += 1
        running_instances.append(instance.id)
    #  terminate all the workers
    for w in range(worker_count):
        id = running_instances[-1]
        ec2.instances.filter(InstanceIds=[id]).terminate()
        running_instances.remove(id)
    #  stop the manager app
    ec2.instances.filter(InstanceIds=[config.manager_app_instance_id]).stop()


@webapp.route('/delete', methods=['GET'])
def delete_application_data():
    #  clear all data in the database
    cursor = mysql.connection.cursor()
    query = "DELETE FROM users"
    cursor.execute(query)
    query = "DELETE FROM images"
    cursor.execute(query)
    query = "UPDATE auto_scaler_settings SET upperthres=100, lowerthres=0, expandratio=1, shrinkratio=1 WHERE id = 1"
    cursor.execute(query)
    mysql.connection.commit()
    cursor.close()
    #  clear all data in the S3 bucket
    s3 = boto3.resource('s3')
    s3.Object(config.S3_BUCKET, config.KEY).delete()
