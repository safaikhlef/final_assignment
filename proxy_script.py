import random
import sys
import mysql.connector
from ping3 import ping

# MySQL Cluster configurations
cluster_manager = {
    'host': 'manager_public_ip',
    'user': 'root',
    'database': 'sakila',
}

cluster_workers = [
    {'host': 'worker_1_public_ip'},
    {'host': 'worker_2_public_ip'},
    {'host': 'worker_3_public_ip'},
]

# Proxy configurations
ping_attempts = 3  # Number of ping attempts to measure response time

def direct_hit(request):
    # Forward modification requests directly to MySQL cluster manager
    try:
        # Execute the SQL query on the database
        conn = mysql.connector.connect(**cluster_manager)
        cursor = conn.cursor()
        cursor.execute(request)
        conn.commit()
        return "Modification request executed on the manager."
    except Exception as e:
        return f"Error in Direct hit implementation: {e}"
    finally:
        cursor.close()
        conn.close()

def random(request):
    # Randomly choose a cluster worker and forward the read request
    random_slave = random.choice(cluster_workers)
    try:
        # Execute the SQL query on the database
        conn = mysql.connector.connect(**random_slave)
        cursor = conn.cursor()
        cursor.execute(request)
        result = cursor.fetchall()
        return result
    except Exception as e:
        return f"Error in Random implementation: {e}"
    finally:
        cursor.close()
        conn.close()

def customized(request):
    # Measure ping time for each cluster worker and choose the one with the lowest response time for read requests
    lowest_ping_time = float('inf')
    best_worker = None

    # Find the worker with the lowest ping time
    for worker in cluster_workers:
        host = worker['host']
        ping_time = ping(host, times=ping_attempts)
        if ping_time is not None and ping_time < lowest_ping_time:
            lowest_ping_time = ping_time
            best_worker = worker

    if best_worker is not None:
        try:
            # Execute the SQL query on the database
            conn = mysql.connector.connect(**best_worker)
            cursor = conn.cursor()
            cursor.execute(request)
            result = cursor.fetchall()
            return result
        except Exception as e:
            return f"Error in Customized implementation: {e}"
        finally:
            cursor.close()
            conn.close()
    else:
        return "No available workers for reading."

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Usage: python3 proxy_script.py <manager_public_ip> <worker_1_public_ip> <worker_2_public_ip> <worker_3_public_ip> <implementation> <request>")
        sys.exit(1)

    manager_public_ip = sys.argv[1]
    worker_1_public_ip = sys.argv[2]
    worker_2_public_ip = sys.argv[3]
    worker_3_public_ip = sys.argv[4]
    implementation = sys.argv[5]
    request = sys.argv[6]

    # Changing the public ip address for the real instances ip addresses that have been passed like arguments to the script
    cluster_manager['host'] = manager_public_ip
    cluster_workers[0]['host'] = worker_1_public_ip
    cluster_workers[1]['host'] = worker_2_public_ip
    cluster_workers[2]['host'] = worker_3_public_ip
    
    # Choose the strategy 
    if implementation == 'Direct hit':
        response = direct_hit(request)
    if implementation == 'Random':
        response = random(request)
    if implementation == 'Customized':
        response = customized(request)

    # Return the response from the query
    print(response)
