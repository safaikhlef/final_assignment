import boto3 
import os
import botocore
import platform
import subprocess
import sys
from botocore.exceptions import ClientError

# create and lunch instances
def lunch_ec2(): 
    # create SSH key_pair named 'bot.pem' 
    keypair_name = create_key_pair()

    # create security group named 'botSecurityGroup' that allows SHH and http traffic 
    security_group_id = create_security_group()

    
    # Lunch 5 instances of type t2.micro 
    # The instance in zone us-east-1a is for the stand-alone and the 4 other ones are for the MySQL Cluster 
    # The instance in zone us-east-1b is for the manager of the the MySQL Cluster 
    # The instance in zones us-east-1c, us-east-1d and us-east-1e are for the workers of the the MySQL Cluster 
    lunched = create_instances('t2.micro', keypair_name, [security_group_id], ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e']) 


# function that creates and saves an ssh key pair. It also gives read only permission to the file  
def create_key_pair():
    key_pair_name = 'bot'
    try:
        keypair = ec2.create_key_pair(KeyName='bot', KeyFormat='pem', KeyType='rsa')
        current_directory = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(current_directory, f'{key_pair_name}.pem')
        
        # save key_pair
        with open(f'{key_pair_name}.pem', 'w') as key_file:
            key_file.write(keypair['KeyMaterial'])
        
        # function to give read only permission
        set_file_permissions(file_path)
        
        print(f"Key pair '{key_pair_name}' created successfully and saved")
        return key_pair_name
    except ec2.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
            return key_pair_name
        else:
            raise 

# function to give read only permission
# (parameter) (string) file_path : path to the file
def set_file_permissions(file_path):

    # read only permissions on windows 
    if platform.system() == 'Windows':
        try:
            subprocess.run(["icacls", file_path, "/inheritance:r", "/grant:r", f"*S-1-5-32-545:(R)"])
        except Exception as e:
            print(f"Failed to set permissions on Windows: {e}")
    else:
        try:
            # Set the file permissions to chmod 400
            os.chmod(file_path, 0o400)
        except Exception as e:
            print(f"Failed to set permissions on Unix-like system: {e}")


# function to create a security group that allows HTTP traffic on port 80 
def create_security_group():

    try:
        # Create a security group allowing HTTP (port 80), HTTPS (port 443), for the containers (port 5000 and 5001) and shh (port 22) traffic
        response = ec2.create_security_group(
            Description='This security group is for the bot',
            GroupName='botSecurityGroup',
        )
        security_group_id = response['GroupId']

        # Authorize inbound traffic for HTTP (port 80) 
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for HTTPS (port 443)
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=443,
            ToPort=443,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for container1 (port 5000) 
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=5000,
            ToPort=5000,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for container2 (port 5001) 
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpProtocol='tcp',
            FromPort=5001,
            ToPort=5001,
            CidrIp='0.0.0.0/0'  # Open to all traffic 
        )
        # Authorize inbound traffic for ssh (port 22)
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [
                        {
                            'CidrIp': '0.0.0.0/0',  # Open to all traffic 
                        },
                    ],
                },
            ],
        )
        return security_group_id
    except Exception as e:
        if "InvalidGroup.Duplicate" in str(e):
            response = ec2.describe_security_groups(
            Filters=[
            {
                'Name': 'group-name',
                'Values': ['botSecurityGroup']
                    }
                ]
            )
            return response['SecurityGroups'][0]['GroupId']
        else:
            print(f"Failed to create security group {e}")


# function to lunch instances with a specific type in multiple availability zones
# (Parameter) (string) instance_type : the type of the instance . Example : 'm4.large'
# (Parameter) (string) keypair_name : The name of the key pair.
# (Parameter) (list of string) security_group_id : The security group ids.
# (Parameter) (list of string) availability_zones : the zones that hosts the EC2 instances
# (return) list of string that contains the instance ids 

def create_instances(instance_type, keypair_name, security_group_id, availability_zones):
    # Machine Image Id. We use : Ubuntu, 22.04 LTS. Id found in aws console  
    image_id = "ami-053b0d53c279acc90"
    response = {}
    try:
        # Launch instances in each availability zone
        for az in availability_zones :
            response = ec2.run_instances(
                ImageId=image_id,  
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=security_group_id,
                KeyName=keypair_name,
                Placement={'AvailabilityZone': az},
                # We need a bigger storage space to be able to install PyTorch
                BlockDeviceMappings=[
                    {
                        'DeviceName': '/dev/sda1',  # Root volume
                        'Ebs': {
                            'VolumeSize': 15,  # Specify the desired storage size in GB
                        },
                    },
                ]
                )
            # Get the instance ID
            instance_id = response['Instances'][0]['InstanceId']
            # wait to create the instance
            ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
            print(f'Launched instance {instance_id} in availability zone {az}')
        
        print(f'all {instance_type} instances are created successfully')       
    except ClientError as e:
        print(f"Failed to create instances:  {e.response['Error']['Message']}")
                
if __name__ == '__main__':
    global ec2
    global aws_console

    print("This script launches overall 4 EC2 workers instances of type M4.Large in Availability Zones : 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e' . And 1 EC2 orchestrator intance in Availability Zone us-east-1a  \n")          
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
    lunch_ec2()