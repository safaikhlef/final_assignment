import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

# Function to setup the proxy server and start the script handling requests
def setup_proxy():
    # Set up the proxy
    # Get the proxy server instance infos
    proxy_public_ip  = get_proxy_infos()
    # Get the MySQL Cluster manager and workers instances infos
    cluster_public_ip = get_cluster_infos()
    # Install the dependencies and copy the script on the proxy server instance
    install_proxy_script(proxy_public_ip, 'bot.pem', cluster_public_ip)

# Function to install the dependencies and copy the script on the instance  
def install_proxy_script(public_ip, key_file, cluster_public_ip):
    try:
        # Copy the proxy script on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r proxy_script.py ubuntu@{public_ip}:/home/ubuntu/'
        os.system(copy_command)

        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install Python on the instance and start the proxy script
        commands = [
            'echo "----------------------- Installing Python and pip ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install python3-pip -y',
            'echo "----------------------- Installing necessary libraries ----------------------------------"',
            'sudo pip install mysql-connector-python ping3',
            'echo "----------------------- Starting the proxy script ----------------------------------"',
            f'python3 proxy_script.py "{cluster_public_ip[0]}" "{cluster_public_ip[1]}" "{cluster_public_ip[2]}" "{cluster_public_ip[3]}"'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully started the proxy script on the instance ---------------------------\n')  
        ssh_client.close()

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

# Function to get the manager and the workers public IP address of the MySQL Cluster
def get_cluster_infos():    
    public_ip_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instances are of type 't2.micro' and in zones us-east-1b, us-east-1c, us-east-1d and us-east-1e, so we only need their information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.micro' and instance['Placement']['AvailabilityZone'] != 'us-east-1a':
                public_ip = instance.get('PublicIpAddress')
                public_ip_list.append(public_ip)
            
    return public_ip_list


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

    setup_proxy()  