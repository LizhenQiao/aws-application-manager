from flask import Flask
webapp = Flask(__name__)
webapp.secret_key = "you-will-never-know-lol"
webapp.jinja_env.auto_reload = True
webapp.config['TEMPLATES_AUTO_RELOAD'] = True
webapp.config['SESSION_TYPE'] = 'filesystem'

from app import main
from app import worker
from app import auto_scaler


####################################################################
#  auto-scaler background process
####################################################################
from app import config
from datetime import datetime, timedelta
import time
import threading
import atexit
import math
import boto3
import os
import mysql.connector
import yaml

db = yaml.load(open('app/static/db.yaml'), Loader=yaml.FullLoader)
dbconnecion = mysql.connector.connect(
    host=db['mysql_host'],
    user=db['mysql_user'],
    password=db['mysql_password'],
    database=db['mysql_db']
)
# print("dbconnecion")

os.environ['AWS_ACCESS_KEY_ID'] = config.KEY
os.environ['AWS_SECRET_ACCESS_KEY'] = config.SECRET
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

upperthres = 100
lowerthres = 0
expandratio = 1
shrinkratio = 1

client = boto3.client('cloudwatch')
elb = boto3.client('elbv2')
ec2 = boto3.resource('ec2')

filters = [
    {
        'Name': 'instance-state-name',
        'Values': ['running', 'pending', 'initilizing']
    },
    {
        "Name": "image-id",
        "Values": [config.AMI_ID]
    }
]



def worker_pool_monitor():
    current_worker_count = 0
    instances = ec2.instances.filter(Filters=filters)
    for instance in instances:
        current_worker_count += 1
    if current_worker_count == 0:  # add a worker if the worker pool is empty
        ec2.create_instances(ImageId=config.AMI_ID,
                            MinCount=1,
                            MaxCount=1,
                            InstanceType='t2.micro',
                            Monitoring={"Enabled": True},
                            KeyName=config.USER_KEY_PAIR,
                            NetworkInterfaces=[
                                {
                                    "DeviceIndex": 0,
                                    "AssociatePublicIpAddress": True,
                                    "SubnetId": config.SUBNET_ID,
                                    "Groups": [config.SECRET_GROUP]
                                }
                            ],
                            UserData= "#!/bin/bash\n /bin/bash /home/ubuntu/start.sh"
                            )
        print("Initializing first worker...")
        time.sleep(240)  # wait for instance initializing phrase
    print('Workers have been initialized.')

    while True:
        worker_count = 0
        instances = ec2.instances.filter(Filters=filters)
        running_instances = []
        for instance in instances:
            worker_count += 1
            running_instances.append(instance.id)
            elb.register_targets(
                TargetGroupArn=config.TARGET_GROUP_ARN,
                Targets=[
                    {
                        "Id": instance.id,
                        "Port": 5000
                    },
                ]
            )

        cursor = dbconnecion.cursor()
        query = "SELECT upperthres, lowerthres, expandratio, shrinkratio FROM auto_scaler_settings WHERE id = 1"
        cursor.execute(query)
        auto_scaler_settings = cursor.fetchall()  # current auto-scaling settings
        upperthres = float(auto_scaler_settings[0][0])  # upper threshold
        lowerthres = float(auto_scaler_settings[0][1])  # lower threshold
        expandratio = float(auto_scaler_settings[0][2])  # expand ratio
        shrinkratio = float(auto_scaler_settings[0][3])  # shrink ratio

        namespace = 'AWS/EC2'
        cpu_utilization = client.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=1.5 * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName='CPUUtilization',
            Namespace=namespace,
            Statistics=['Average'],
            Dimensions=[{'Name': 'ImageId', 'Value': config.AMI_ID}],
        )
        average_cpu_utilization = 0
        for point in cpu_utilization['Datapoints']:
            if 'Average' in point:
                average_cpu_utilization = point['Average']  # current average cpu utilization
        print("average_cpu_utilization: {}".format(average_cpu_utilization))

        updated_worker_count = 0
        if average_cpu_utilization > upperthres:
            updated_worker_count = math.ceil(worker_count * expandratio)
            if updated_worker_count > 6:
                updated_worker_count = 6
        elif average_cpu_utilization < lowerthres:
            updated_worker_count = math.ceil(worker_count * shrinkratio)
            if updated_worker_count < 1:
                updated_worker_count = 1
        else:
            updated_worker_count = worker_count
        worker_diff = updated_worker_count - worker_count
        if worker_diff > 0:  # case expand the worker pool
            print("Creating new workers...")
            ec2.create_instances(ImageId=config.AMI_ID,
                                    MinCount=1,
                                    MaxCount=worker_diff,
                                    InstanceType='t2.micro',
                                    Monitoring={"Enabled": True},
                                    KeyName=config.USER_KEY_PAIR,
                                    NetworkInterfaces=[
                                        {
                                            "DeviceIndex": 0,
                                            "AssociatePublicIpAddress": True,
                                            "SubnetId": config.SUBNET_ID,
                                            "Groups": [config.SECRET_GROUP]
                                        }
                                    ],
                                    UserData= "#!/bin/bash\n /bin/bash /home/ubuntu/start.sh"
                                    )
            print("New worker has been created. Waiting for initializing...")
            time.sleep(240)  # wait for instance initializing phrase
            print("New worker has been initialized.")
        elif worker_diff < 0:  # case shrink the worker pool
            worker_to_remove = -worker_diff
            print("Shrinking workers...")
            for w in range(worker_to_remove):
                id = running_instances[-1]  # point to the last instance in the list
                ec2.instances.filter(InstanceIds=[id]).terminate()
                running_instances.remove(id)
            time.sleep(60)
            print("Workers has been deleted.")
        time.sleep(15)



def terminate():
    global thread
    thread.cancel()


#  start the thread
global thread
thread = threading.Thread(target=worker_pool_monitor)
thread.start()
atexit.register(terminate)
