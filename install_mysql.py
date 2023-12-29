import boto3 
import os
import paramiko
import botocore
import sys
import json
from botocore.exceptions import ClientError

# Function to install MySQL, do the right setup for the MySQL and benchmark on the stand-alone instance and the MySQL Cluster instances
def setup_mysql():
    # Set up the sand-alone
    # Get the stand-alone instance infos
    stand_alone_public_ip  = get_stand_alone_infos()
    # Install MySQL on the stand-alone instance
    install_mysql_stand_alone(stand_alone_public_ip, 'bot.pem')

    # Set up the cluster
    # Get the manager of the the MySQL Cluster instance infos
    manager_public_ip = get_manager_infos()
    # Get the workers of the the MySQL Cluster instances infos
    workers_infos = get_workers_infos()
    # Install MySQL Cluster and setup the instance to be the manager of the cluster
    install_mysql_manager(manager_public_ip, 'bot.pem', workers_infos)

    # Benchmark
    # Test the performance of MySQL on the stand-alone instance
    benchmark_stand_alone(stand_alone_public_ip, 'bot.pem')
    # Test the performance of MySQL on the MySQL Cluster instances
    benchmark_cluster(manager_public_ip, 'bot.pem')

# Function to install MySQL stand-alone on the instance  
def install_mysql_stand_alone(public_ip, key_file):
    try:
        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

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
def install_mysql_manager(public_ip, key_file, public_ip_workers):
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

# Function to test the performance of the MySQL stand-alone server
def benchmark_stand_alone(public_ip, key_file):
    try:
        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to benchmark MySQL stand-alone server using sysbench
        commands = [
            'echo "----------------------- Generating the table for tests ----------------------------------"',
            'sysbench --test=oltp --oltp-table-size=1000000 --mysql-db=sakila --mysql-user=root prepare',
            'echo "----------------------- Begin performance tests ----------------------------------"',
            'sysbench --test=oltp --oltp-table-size=1000000 --oltp-test-mode=complex --oltp-read-only=off --num-threads=6 --max-time=60 --max-requests=0 --mysql-db=sakila --mysql-user=root run > benchmark_stand_alone.txt',
            'echo "----------------------- Clean up test area ----------------------------------"',
            'sysbench --test=oltp --mysql-db=sakila --mysql-user=root cleanup',
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Copy the benchmarking file on the instance to the file system of the host machine
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r ubuntu@{public_ip}:benchmark_stand_alone.txt .'
        os.system(copy_command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully benchmarked the MySQL stand-alone server ---------------------------\n')  
        ssh_client.close()

# Function to test the performance of the MySQL Cluster
def benchmark_cluster(public_ip, key_file):
    try:
        # Initialize SSH communication with the instance
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(public_ip, username='ubuntu', key_filename=key_file)

        # Commands to benchmark MySQL Cluster using sysbench
        commands = [
            'echo "----------------------- Generating the table for tests ----------------------------------"',
            'sysbench --test=oltp --oltp-table-size=1000000 --mysql-db=sakila --mysql-user=root --mysql_storage_engine=ndbcluster prepare',
            'echo "----------------------- Begin performance tests ----------------------------------"',
            'sysbench --test=oltp --oltp-table-size=1000000 --oltp-test-mode=complex --oltp-read-only=off --num-threads=6 --max-time=60 --max-requests=0 --mysql-db=sakila --mysql-user=root --mysql_storage_engine=ndbcluster run > benchmark_cluster.txt',
            'echo "----------------------- Clean up test area ----------------------------------"',
            'sysbench --test=oltp --mysql-db=sakila --mysql-user=root --mysql_storage_engine=ndbcluster cleanup',
        ]
        command = '; '.join(commands)
        stdin, stdout, stderr = ssh_client.exec_command(command)

        # Copy the benchmarking file on the instance to the file system of the host machine
        copy_command = f'scp -o StrictHostKeyChecking=no -i {key_file} -r ubuntu@{public_ip}:benchmark_cluster.txt .'
        os.system(copy_command)

    finally:  
        print(stdout.read().decode('utf-8'))
        print(f'-------------- Successfully benchmarked the MySQL stand-alone server ---------------------------\n')  
        ssh_client.close()

# Function to get the MySQL stand-alone public IP address 
def get_stand_alone_infos(): 
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is of type 't2.micro' and in the zone us-east-1a, so we only need its information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.micro' and instance['Placement']['AvailabilityZone'] == 'us-east-1a':
                public_ip = instance.get('PublicIpAddress')
            
    return public_ip

# Function to get the MySQL Cluster manager public IP address 
def get_manager_infos(): 
    public_ip = ''
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instance is of type 't2.micro' and in the zone us-east-1b, so we only need its information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.micro' and instance['Placement']['AvailabilityZone'] == 'us-east-1b':
                public_ip = instance.get('PublicIpAddress')
            
    return public_ip

# Function to get workers public IP address 
def get_workers_infos():    
    public_ip_list = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
             # Get only instances currently running
             # The instances are of type 't2.micro' and in zones us-east-1c, us-east-1d and us-east-1e, so we only need their information
            if instance['State']['Name'] == 'running' and instance['InstanceType'] == 't2.micro' and instance['Placement']['AvailabilityZone'] != 'us-east-1a' and instance['Placement']['AvailabilityZone'] != 'us-east-1b':
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