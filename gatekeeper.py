import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

# Function to setup the gatekeeper server and start the app handling requests
def setup_gatekeeper():
    # Set up the gatekeeper
    # Get the gatekeeper server instance infos
    gatekeeper_public_ip  = get_gatekeeper_infos()
    # Get the trusted host server instance infos
    trusted_host_public_ip  = get_trusted_host_infos()
    # Install the dependencies and copy the app code on the gatekeeper server instance
    start_gatekeeper(gatekeeper_public_ip, 'bot.pem', trusted_host_public_ip)

    # Set up the trusted host
    # Get the proxy server instance infos
    proxy_public_ip  = get_proxy_infos()
    # Install the dependencies and copy the app code on the trusted host server instance
    start_trusted_host(trusted_host_public_ip, 'bot.pem', proxy_public_ip, gatekeeper_public_ip)

    # Set up the proxy
    # Install the dependencies and copy the app code on the proxy server instance
    start_proxy(trusted_host_public_ip, 'bot.pem', proxy_public_ip, gatekeeper_public_ip)

# Function to install the dependencies and copy the app code on the instance  
def start_gatekeeper(public_ip, key_file, trusted_host_public_ip):
    try:
        # Copy the gatekeeper Flask app code on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r gatekeeper_app.py ubuntu@{public_ip}:/home/ubuntu/'
        os.system(copy_command)

        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to start the Flask gatekeeper app 
        commands = [
            'echo "----------------------- Installing Python and pip ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'echo "----------------------- Installing necessary libraries ----------------------------------"',
            'sudo pip install Flask requests',
            'echo "----------------------- Launching the Flask app ----------------------------------"',
            f'export TRUSTED_HOST_URL=http://{trusted_host_public_ip}:5000"', # Environment variable for the URL
            'nohup sudo python3 gatekeeper_app.py > /dev/null 2>&1 &'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully launched the gatekeeper app on the instance ---------------------------\n')  
        ssh_client.close()

# Function to install the dependencies and copy the app code on the instance  
def start_trusted_host(public_ip, key_file, proxy_public_ip, gatekeeper_public_ip):
    try:
        # Copy the trusted host Flask app code on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r trusted_host_app.py ubuntu@{public_ip}:/home/ubuntu/'
        os.system(copy_command)

        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to start the Flask trusted host app 
        commands = [
            'echo "----------------------- Installing Python and pip ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'echo "----------------------- Installing necessary libraries ----------------------------------"',
            'sudo pip install Flask requests',
            'echo "----------------------- Launching the Flask app ----------------------------------"',
            f'export PROXY_URL=http://{proxy_public_ip}:5001"', # Environment variable for the URL
            f'export GATEKEEPER_IP="{gatekeeper_public_ip}"', # Environment variable for the gatekeeper ip address
            'nohup sudo python3 trusted_host_app.py > /dev/null 2>&1 &'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully launched the trusted host app on the instance ---------------------------\n')  
        ssh_client.close()

# Function to install the dependencies and copy the app code on the instance  
def start_proxy(public_ip, key_file, proxy_public_ip, gatekeeper_public_ip):
    try:
        # Copy the trusted host Flask app code on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r proxy_app.py ubuntu@{public_ip}:/home/ubuntu/'
        os.system(copy_command)

        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to start the Flask trusted host app 
        commands = [
            'echo "----------------------- Installing Python and pip ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'echo "----------------------- Installing necessary libraries ----------------------------------"',
            'sudo pip install Flask requests',
            'echo "----------------------- Launching the Flask app ----------------------------------"',
            f'export TRUSTED_HOST_IP="{gatekeeper_public_ip}"', # Environment variable for the trusted ip address
            'nohup sudo python3 proxy_app.py > /dev/null 2>&1 &'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully launched the trusted host app on the instance ---------------------------\n')  
        ssh_client.close()

# Function to get the gatekeeper public IP address 
def get_gatekeeper_infos(): 
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is of type 't2.large' and in the zone us-east-1b, so we only need its information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.large' and instance['Placement']['AvailabilityZone'] == 'us-east-1b':
                public_ip = instance.get('PublicIpAddress')
            
    return public_ip

# Function to get the trusted host public IP address 
def get_trusted_host_infos(): 
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is of type 't2.large' and in the zone us-east-1c, so we only need its information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.large' and instance['Placement']['AvailabilityZone'] == 'us-east-1c':
                public_ip = instance.get('PublicIpAddress')
            
    return public_ip

# Function to get the proxy public IP address 
def get_proxy_infos(): 
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is of type 't2.large' and in the zone us-east-1a, so we only need its information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.large' and instance['Placement']['AvailabilityZone'] == 'us-east-1a':
                public_ip = instance.get('PublicIpAddress')
            
    return public_ip

if __name__ == '__main__':
    global ec2
    global aws_console
    
    print("This script install Docker and start two containers on every instances \n")          
    
    if len(sys.argv) != 5:
        print("Usage: python lunch.py <aws_access_key_id> <aws_secret_access_key> <aws_session_token> <aws_region>")
        sys.exit(1)

    aws_access_key_id = sys.argv[1]
    aws_secret_access_key = sys.argv[2]
    aws_session_token = sys.argv[3]
    aws_region = sys.argv[4]
    
    # Create a a boto3 session with credentials 
    aws_console = boto3.session.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token, 
        region_name=aws_region
    )
    # Client for ec2 instances
    ec2 = aws_console.client('ec2')

    setup_gatekeeper()  