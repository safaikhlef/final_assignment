from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Get the trusted host ip address from the environment variable
trusted_host_ip = os.environ.get('TRUSTED_HOST_IP')

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

        # Get the SQL query from the request
        query = incoming_request_data['request']

        # Check if the query is safe by validating that is one of the allowed operations
        query_safe = is_allowed_operation(query)
 
        # If the query is not safe, raise an error and do not forward the request to the proxy
        if not query_safe:
            raise ValueError("The request is denied. Operation not allowed.")

        # Forward the request to the proxy if it is safe
        response = requests.get(proxy_url + '/process_request', json=incoming_request_data)

        # Return the response from the proxy
        return jsonify({'status': 'success', 'response': response.json()})
    
    except Exception as e:
        # Return the error message
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/process_request', methods=['POST'])
def forward_request():
    try:
       # Get the incoming request data
        incoming_request_data = request.json

        # Get the SQL query from the request
        query = incoming_request_data['request']

        # Check if the query is safe by validating that is one of the allowed operations
        query_safe = is_allowed_operation(query)
 
        # If the query is not safe, raise an error and do not forward the request to the proxy
        if not query_safe:
            raise ValueError("The request is denied. Operation not allowed.")

        # Forward the request to the proxy if it is safe
        response = requests.post(proxy_url + '/process_request', json=incoming_request_data)

        # Return the response from the proxy
        return jsonify({'status': 'success', 'response': response.json()})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    # Make sure the app is only accessible to requests coming from the trusted host
    app.run(host=trusted_host_ip, port=5001)
