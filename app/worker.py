from flask import render_template, request, redirect, flash, url_for, session
from app import webapp, config
from app.config import S3_KEY, S3_SECRET, S3_BUCKET, S3_LOCATION
import boto3
s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET
)


@webapp.route('/manager/workers', methods=['GET', 'POST'])
def worker_list():
    if 'manager_name' in session:
        ec2 = boto3.resource('ec2')
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
        instances = ec2.instances.filter(Filters=filters)

    return render_template("manager/worker_list.html", title="Worker List", instances=instances)


@webapp.route('/manager/add', methods=['POST'])
def worker_add():
    if 'manager_name' in session:
        worker_count = 0
        ec2 = boto3.resource('ec2')
        ec2.create_instances(ImageId=config.ami_id, MinCount=1, MaxCount=1,
                             InstanceType='t2.micro', SubnetId=config.subnet_id)
    return redirect(url_for('worker_list'))


@webapp.route('/manager/delete/<id>', methods=['POST'])
def worker_remove(id):
    if 'manager_name' in session:
        ec2 = boto3.resource('ec2')
        ec2.instances.filter(InstanceIds=[id]).terminate()

    return redirect(url_for('worker_list'))
