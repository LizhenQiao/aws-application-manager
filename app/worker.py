from flask import render_template, request, redirect, flash, url_for, session
from app import webapp, config
from datetime import datetime, timedelta
from operator import itemgetter
import boto3

filters = [
    {
        "Name": "instance-state-name",
        "Values": ["initializing", "pending", "running"]
    },
    {
        "Name": "image-id",
        "Values": [config.ami_id]
    }
]


@webapp.route('/manager/workers', methods=['GET', 'POST'])
def worker_list():
    if 'manager_name' in session:
        ec2 = boto3.resource('ec2')
        instances = ec2.instances.filter(Filters=filters)

    return render_template("manager/worker_list.html", title="Worker List",
                           instances=instances)


@webapp.route('/manager/workers/<id>', methods=['GET'])
def worker_view(id):
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(id)
    client = boto3.client('cloudwatch')
    namespace = 'AWS/EC2'
    cpu_utilization = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='CPUUtilization',
        Namespace=namespace,
        Statistics=['Sum'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    cpu_utilization_stats = []
    for point in cpu_utilization['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_utilization_stats.append([time, point['Sum']])
    cpu_utilization_stats = sorted(cpu_utilization_stats, key=itemgetter(0))

    network_packets_in = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkPacketsIn',
        Namespace=namespace,
        Statistics=['Average'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    network_packets_in_stats = []
    for point in network_packets_in['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        network_packets_in_stats.append([time, point['Average']])
    network_packets_in_stats = sorted(network_packets_in_stats, key=itemgetter(0))

    return render_template("manager/worker_view.html", title="Worker Info",
                           instance=instance,
                           cpu_utilization_stats=cpu_utilization_stats,
                           network_packets_in_stats=network_packets_in_stats)


# TODO: Fix - add && delete UnauthorizedOperation
@webapp.route('/manager/add', methods=['POST'])
def worker_add():
    if 'manager_name' in session:
        worker_count = 0
        ec2 = boto3.resource('ec2')
        instances = ec2.instances.filter(Filter=filters)
        for instance in instances:
            worker_count += 1
        if worker_count < 7:
            ec2.create_instances(ImageId=config.ami_id, MinCount=1, MaxCount=1,
                                 InstanceType='t2.micro', SubnetId=config.subnet_id)

    return redirect(url_for('worker_list'))


@webapp.route('/manager/delete/<id>', methods=['POST'])
def worker_remove(id):
    if 'manager_name' in session:
        worker_count = 0
        ec2 = boto3.resource('ec2')
        instances = ec2.instances.filter(Filter=filters)
        for instance in instances:
            worker_count += 1
        if worker_count > 0:
            ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('worker_list'))
