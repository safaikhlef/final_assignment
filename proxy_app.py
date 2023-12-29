from flask import Flask, request, jsonify
import requests
import os
import subprocess

app = Flask(__name__)

# Get the trusted host ip address from the environment variable
trusted_host_ip = os.environ.get('TRUSTED_HOST_IP')
# Get the cluster manager ip address from the environment variable
cluster_manager_ip = os.environ.get('CLUSTER_MANAGER_IP')
# Get the cluster worker_1 ip address from the environment variable
cluster_worker_1_ip = os.environ.get('CLUSTER_WORKER_1_IP')
# Get the cluster worker_2 ip address from the environment variable
cluster_worker_2_ip = os.environ.get('CLUSTER_WORKER_2_IP')
# Get the cluster worker_3 ip address from the environment variable
cluster_worker_3_ip = os.environ.get('CLUSTER_WORKER_3_IP')
# Get the implementation strategy chosen from the environment variable
implementation = os.environ.get('IMPLEMENTATION')

def is_allowed_operation(user_input):
    # Only allow SELECT, INSERT and UPDATE operations
    allowed_operations = ['SELECT', 'INSERT', 'UPDATE']
    # Check if the query start with one of those key word
    operation = user_input.strip().split()[0].upper()
    return operation in allowed_operations

@app.route('/process_request', methods=['GET'])
def forward_request():
    try:
        # Get the incoming request data
        incoming_request_data = request.json

        # If the request is GET, then it is not modifying the database, 
        # so we forward the request to a cluster worker based on the selected implementation
        # The choice of implementation is kept in the environnement variable IMPLEMENTATION
        # By default, 'Customized' has been selected here, but it can be changed

        # Double check that the request is not modifying the database
        # If it doesn't start with 'select', then it is modifying the database,
        # In that case we select the 'Direct hit' implementation to forward it directly to the cluster manager 
        if not incoming_request_data.strip().lower().startswith('select'):
            implementation = 'Direct hit'

        # Use the script proxy_script.py to implement the strategy and execute the query
        result = subprocess.run(["python3", "./proxy_script.py"] + [cluster_manager_ip, cluster_worker_1_ip, cluster_worker_2_ip,\
                                                                    cluster_worker_3_ip, implementation, incoming_request_data], capture_output=True, text=True, check=True)
        # Get the result of the query from stdout
        result = result.stdout.strip()

        # Reset implementation to its default value
        implementation = os.environ.get('IMPLEMENTATION')

        # Return the response from the cluster worker
        return jsonify({'status': 'success', 'response': result.json()})
    
    except Exception as e:
        # Return the error message
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/process_request', methods=['POST'])
def forward_request():
    try:
       # Get the incoming request data
        incoming_request_data = request.json

        # If the request is POST, then it is modifying the database, 
        # so we automatically forward the request to the cluster manager
        # In that case we select the 'Direct hit' implementation to forward it directly to the cluster manager
        implementation = 'Direct hit'

        # Use the script proxy_script.py to implement the strategy and execute the query
        result = subprocess.run(["python3", "./proxy_script.py"] + [cluster_manager_ip, cluster_worker_1_ip, cluster_worker_2_ip,\
                                                                    cluster_worker_3_ip, implementation, incoming_request_data], capture_output=True, text=True, check=True)
        # Get the result of the query from stdout
        result = result.stdout.strip()

        # Reset implementation to its default value
        implementation = os.environ.get('IMPLEMENTATION')

        # Return the response from the cluster manager
        return jsonify({'status': 'success', 'response': result.json()})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # Make sure the app is only accessible to requests coming from the trusted host
    app.run(host=trusted_host_ip, port=5001)
