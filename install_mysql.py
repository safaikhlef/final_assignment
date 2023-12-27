import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

# Function to deploy the ML app in instance via SSH and save the containers informations in the file info.json
def setup_mysql():
    # Get the stand_alone instance infos
    stand_alone_instance_id, stand_alone_public_ip  = get_stand_alone_infos()
    # Install MySQL on the stand-alone instance
    install_mysql_stand_alone(stand_alone_instance_id, stand_alone_public_ip, 'bot.pem')

    # Get the manager of the the MySQL Cluster instance infos
    manager_instance_id, manager_public_ip  = get_manager_infos()
    # Get the workers of the the MySQL Cluster instances infos
    workers_infos  = get_workers_infos()
    # Install MySQL Cluster and setup the instance to be the manager of the cluster
    install_mysql_manager(manager_instance_id, manager_public_ip, 'bot.pem', workers_infos)

    # install_mysql_manager(manager_instance_id, manager_public_ip, 'bot.pem', manager_public_ip)

    # Get the MySQL Cluster instances infos
    #instance_infos = get_instance_infos()
    index = 1
    # Install the MySQL Cluster
    # for instance in instance_infos :   
    #     instance_id, public_ip = instance   
    #     start_containers(instance_id, public_ip, 'bot.pem')
    #     containers = {f'container{index}': {'ip':public_ip, "port":"5000", "status": "free"},f'container{index+1}': {'ip':public_ip, "port":"5001", "status": "free"}}
    #     write_intance_infos("info.json",containers)
    #     index += 2 

# Function to install MySQL stand-alone on the instance  
def install_mysql_stand_alone(instance_id, public_ip, key_file):
    try:
        # Copy the necessary files to start the containers on the instance
        # copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r ./containers ubuntu@{public_ip}:/home/ubuntu/'
        # print(f'Copying local Flask app code and Dockerfile to {instance_id}...')
        # os.system(copy_command)

        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # # Predefine MySQL root password to avoid interactive prompt
        # mysql_root_password = "password_stand_alone"
        # predefine_commands = [
        #     f'echo "mysql-server mysql-server/root_password password {mysql_root_password}" | sudo debconf-set-selections',
        #     f'echo "mysql-server mysql-server/root_password_again password {mysql_root_password}" | sudo debconf-set-selections'
        # ]
        # predefine_command = '; '.join(predefine_commands)
        # ssh_client.exec_command(predefine_command)

        # Commands to install MySQL Server in the instance
        commands = [
            'echo "----------------------- Installing MySQL ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install mysql-server sysbench -y',
            'echo "----------------------- Address security concerns and make MySQL safer ----------------------------------"',
            'sudo mysql_secure_installation -y',
            'echo "----------------------- Install Sakila database ----------------------------------"',
            'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',
            'tar -xf sakila-db.tar.gz',
            'rm sakila-db.tar.gz',
            'sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"',
            'sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"',
            'sudo mysql -e "USE sakila;"'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully installed MySQL on the instance ---------------------------\n')  
        ssh_client.close()

# Function to install MySQL Cluster and setup the manager instance  
def install_mysql_manager(instance_id, public_ip, key_file, public_ip_workers):
    try:
        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install MySQL Cluster and setup the manager instance 
        commands = [
            'echo "----------------------- Uninstall any existing Mysql packages ----------------------------------"',
            'service mysqld stop',
            'apt-get remove mysql-server mysql mysql-devel',
            'echo "----------------------- Download and Extract MySQL Cluster Binaries ----------------------------------"',
            'cd /opt/mysqlcluster/home',
            'wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz'
            'tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
            'ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc',
            'echo "----------------------- Setup Executable Path Globally ----------------------------------"',
            'echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc" > /etc/profile.d/mysqlc.sh',
            'echo "export PATH=$MYSQLC_HOME/bin:$PATH" >> /etc/profile.d/mysqlc.sh',
            'source /etc/profile.d/mysqlc.sh',
            'sudo apt-get update && sudo apt-get -y install libncurses5 sysbench',
            'echo "----------------------- Create the Deployment Directory and Setup Config Files ----------------------------------"',
            'mkdir -p /opt/mysqlcluster/deploy',
            'cd /opt/mysqlcluster/deploy',
            'mkdir conf',
            'mkdir mysqld_data',
            'mkdir ndb_data',
            'cd conf',
            'cat <<EOF > my.cnf',
            '[mysqld]',
            'ndbcluster',
            'datadir=/opt/mysqlcluster/deploy/mysqld_data',
            'basedir=/opt/mysqlcluster/home/mysqlc',
            'port=3306',
            'EOF',
            'cat <<EOF > config.ini',
            '[ndb_mgmd]',
            f'hostname={public_ip}',
            'datadir=/opt/mysqlcluster/deploy/ndb_data',
            'nodeid=1',
            '',
            '[ndbd default]',
            'noofreplicas=3',
            'datadir=/opt/mysqlcluster/deploy/ndb_data',
            '',
            '[ndbd]',
            f'hostname={public_ip_workers[0]}',
            'nodeid=3',
            '',
            '[ndbd]',
            f'hostname={public_ip_workers[1]}',
            'nodeid=4',
            '',
            '[ndbd]',
            f'hostname={public_ip_workers[2]}',
            'nodeid=5',
            '',
            '[mysqld]',
            'nodeid=50',
            'EOF',
            'echo "----------------------- Initialize the Database ----------------------------------"',
            'cd /opt/mysqlcluster/home/mysqlc',
            'scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data',
            'echo "----------------------- Start management node ----------------------------------"',
            'sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Install MySQL Cluster and setup the instance to be the workers of the cluster
        for public_ip_worker in public_ip_workers:
            install_mysql_workers(public_ip_worker, 'bot.pem', public_ip)

        # Commands to start the SQL node once the data nodes are setup
        commands = [
            'echo "----------------------- Start SQL node ----------------------------------"',
            'mysqld --defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf --user=root &',
            'echo "----------------------- Install Sakila database ----------------------------------"',
            'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',
            'tar -xf sakila-db.tar.gz',
            'rm sakila-db.tar.gz',
            'sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"',
            'sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"',
            'sudo mysql -e "USE sakila;"'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully installed MySQL on the instance ---------------------------\n')  
        ssh_client.close()

# Function to install MySQL Cluster and setup the workers instance 
def install_mysql_workers(public_ip, key_file, public_ip_manager):
    try:
        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install MySQL Cluster and setup the workers instance 
        commands = [
            'echo "----------------------- Uninstall any existing Mysql packages ----------------------------------"',
            'service mysqld stop',
            'apt-get remove mysql-server mysql mysql-devel',
            'echo "----------------------- Download and Extract MySQL Cluster Binaries ----------------------------------"',
            'cd /opt/mysqlcluster/home',
            'wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz'
            'tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
            'ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc',
            'echo "----------------------- Setup Executable Path Globally ----------------------------------"',
            'echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc" > /etc/profile.d/mysqlc.sh',
            'echo "export PATH=$MYSQLC_HOME/bin:$PATH" >> /etc/profile.d/mysqlc.sh',
            'source /etc/profile.d/mysqlc.sh',
            'sudo apt-get update && sudo apt-get -y install libncurses5 sysbench',
            'echo "----------------------- Create NDB DATA directory ----------------------------------"',
            'mkdir -p /opt/mysqlcluster/deploy/ndb_data',
            'echo "----------------------- Start data node ----------------------------------"',
            f'ndbd -c {public_ip_manager}:1186'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully installed MySQL on the instance ---------------------------\n')  
        ssh_client.close()

# Function to copy the ML app code, install docker, and start containers in the instance  
def start_containers(instance_id, public_ip, key_file):
    try:
        # Copy the necessary files to start the containers on the instance
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r ./containers ubuntu@{public_ip}:/home/ubuntu/'
        print(f'Copying local Flask app code and Dockerfile to {instance_id}...')
        os.system(copy_command)

        # intialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to install Docker Engine in the instance and start the two containers running the ML flask app
        commands = [
            'echo "----------------------- adding Dockers official GPG key ----------------------------------"',
            'sudo apt-get update -y',
            'sudo apt-get install ca-certificates curl gnupg -y',
            'sudo install -m 0755 -d /etc/apt/keyrings',
            'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            'sudo chmod a+r /etc/apt/keyrings/docker.gpg',
            'echo "----------------------- adding the repository to Apt sources ----------------------------------"',
            'echo \
                "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
                "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
                sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
            'sudo apt-get update -y',
            'echo "----------------------- instaling Docker packages and Docker compose ----------------------------------"',
            'sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y',
            'sudo apt-get install docker-compose-plugin',
            'echo "----------------------- starting containers ----------------------------------"',
            'cd containers',
            'sudo docker compose up -d'
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- successfully started two containers and application running ---------------------------\n')  
        ssh_client.close()

def write_intance_infos(file_path, instance_info):
    try:
        with open(file_path, 'r') as file:
            # Check if the file is empty
            file_content = file.read()
            if not file_content:
                data = {}
            else:
                # Load the existing data from the file
                data = json.loads(file_content)
        
        data.update(instance_info)
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f'File "{file_path}" with {instance_info} updated successfully.')

    except FileNotFoundError:
        with open(file_path, 'w') as file:
            json.dump(instance_info, file, indent=4)
        
        print(f'File "{file_path}" created successfully.')

    except Exception as e:
        print(f'Error: {e}')

# Function to get the MySQL stand-alone instance id and public IP address 
def get_stand_alone_infos(): 
    instance_id = ''
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is in the zone us-east-1a, so we only need its information
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] == 'us-east-1a':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
            
    return (instance_id, public_ip)

# Function to get the MySQL Cluster manager instance id and public IP address 
def get_manager_infos(): 
    instance_id = ''
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is in the zone us-east-1b, so we only need its information
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] == 'us-east-1b':
                instance_id = instance.get('InstanceId')
                public_ip = instance.get('PublicIpAddress')
            
    return (instance_id, public_ip)

# Function to get workers instance id and public IP address 
def get_workers_infos():    
    public_ip_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instances are in zones us-east-1c, us-east-1d and us-east-1e, so we only need their information
            if instance['State']['Name'] == 'running' and instance['Placement']['AvailabilityZone'] != 'us-east-1a' and instance['Placement']['AvailabilityZone'] != 'us-east-1b':
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

    setup_mysql()  