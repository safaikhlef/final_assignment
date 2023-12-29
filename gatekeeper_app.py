from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Trusted host configuration
# Get the trusted host URL from the environment variable
trusted_host_url = os.environ.get('TRUSTED_HOST_URL')

@app.route('/', methods=['GET'])
def forward_request():
    try:
        # Get the incoming request data
        incoming_request_data = request.json

        # Forward the request to the trusted host
        response = requests.get(trusted_host_url + '/verify_request', json=incoming_request_data)

        # Return the response from the trusted host
        return jsonify({'status': 'success', 'response': response.json()})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/', methods=['POST'])
def forward_request():
    try:
        # Get the incoming request data
        incoming_request_data = request.json

        # Forward the request to the trusted host
        response = requests.post(trusted_host_url + '/verify_request', json=incoming_request_data)

        # Return the response from the trusted host
        return jsonify({'status': 'success', 'response': response.json()})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
