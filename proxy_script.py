import random
import time
import sys
import mysql.connector
from ping3 import ping

# MySQL Cluster configurations
mysql_manager = {
    'host': 'manager_public_ip',
    'user': 'root',
    'database': 'sakila',
}

mysql_workers = [
    {'host': 'worker_1_public_ip'},
    {'host': 'worker_2_public_ip'},
    {'host': 'worker_3_public_ip'},
]

# Proxy configurations
proxy_server = 't2.large_instance_ip'  # Replace with your proxy server IP
ping_attempts = 3  # Number of ping attempts to measure response time

def direct_hit(request):
    # Forward modification requests directly to MySQL master
    try:
        conn = mysql.connector.connect(**mysql_manager)
        cursor = conn.cursor()
        cursor.execute(request)
        conn.commit()
        return "Modification request executed on the master."
    except Exception as e:
        return f"Error in direct_hit: {e}"
    finally:
        cursor.close()
        conn.close()

def random_strategy(request):
    # Randomly choose a slave node and forward the read request
    random_slave = random.choice(mysql_workers)
    try:
        conn = mysql.connector.connect(**random_slave)
        cursor = conn.cursor()
        cursor.execute(request)
        result = cursor.fetchall()
        return result
    except Exception as e:
        return f"Error in random_strategy: {e}"
    finally:
        cursor.close()
        conn.close()

def customized_strategy(request):
    # Measure ping time for each slave and choose the one with the lowest response time for read requests
    if request.strip().lower().startswith('select'):
        lowest_ping_time = float('inf')
        best_slave = None

        for slave in mysql_workers:
            host = slave['host']
            ping_time = ping(host, times=ping_attempts)
            if ping_time is not None and ping_time < lowest_ping_time:
                lowest_ping_time = ping_time
                best_slave = slave

        if best_slave is not None:
            try:
                conn = mysql.connector.connect(**best_slave)
                cursor = conn.cursor()
                cursor.execute(request)
                result = cursor.fetchall()
                return result
            except Exception as e:
                return f"Error in customized_strategy: {e}"
            finally:
                cursor.close()
                conn.close()
        else:
            return "No available slaves for reading."

    else:
        return "Modification requests are only allowed on the master."

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 proxy_script.py <manager_public_ip> <worker_1_public_ip> <worker_2_public_ip> <worker_3_public_ip>")
        sys.exit(1)

    manager_public_ip = sys.argv[1]
    worker_1_public_ip = sys.argv[2]
    worker_2_public_ip = sys.argv[3]
    worker_3_public_ip = sys.argv[4]

    # Changing the public ip address for the real instances ip addresses that have been passed like arguments to the script
    mysql_manager['host'] = manager_public_ip
    mysql_workers[0]['host'] = worker_1_public_ip
    mysql_workers[1]['host'] = worker_2_public_ip
    mysql_workers[2]['host'] = worker_3_public_ip

    # Example usage
    modification_request = "UPDATE your_table SET column='value' WHERE condition;"
    read_request = "SELECT * FROM your_table;"
    
    # Choose the strategy (direct_hit for modification, random_strategy or customized_strategy for reading)
    strategy = direct_hit if modification_request.strip().lower().startswith('update') else customized_strategy

    result = strategy(modification_request) if modification_request.strip().lower().startswith('update') else strategy(read_request)
    print(result)
