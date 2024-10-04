import json
import base64
import requests
import os

content_type = 'application/json'
jamf_pro_url = 'https://x.jamfcloud.com'
jamf_pro_username = os.environ.get('user')
jamf_pro_password = os.environ.get('pwd')
persistent = requests.Session()

def create_jamf_token(jamf_pro_url, jamf_pro_username, jamf_pro_password):
    print('Attempting to auth to Jamf Pro for API Token')
    jamf_pro_auth = jamf_pro_username + ':' + jamf_pro_password
    jamf_pro_base64 = base64.b64encode(jamf_pro_auth.encode()).decode()
    jamf_pro_token_url = f'{jamf_pro_url}/api/v1/auth/token'
    auth_headers = {
        "Authorization": 'Basic ' + jamf_pro_base64,
        "Content-Type": content_type,
        "Accept": content_type
    }

    jamf_pro_token_request = persistent.post(jamf_pro_token_url, headers=auth_headers)
    jamf_pro_token_request_status_code = jamf_pro_token_request.status_code
    if jamf_pro_token_request_status_code != 200:
        print(f'Unable to contact Jamf Pro for Auth token {jamf_pro_token_request_status_code}')
        return False

    jamf_pro_token = jamf_pro_token_request.json()
    jamf_pro_token = jamf_pro_token['token']
    return jamf_pro_token

def get_prestage_version_lock(auth_token, ios_device_type):
    url = f'{jamf_pro_url}/api/v2/mobile-device-prestages/{ios_device_type}'

    headers = {
        "authorization": f'Bearer {auth_token}',
        "accept": "application/json",
        "content-type": "application/json"
    }

    response = requests.get(url, headers=headers)
    version_lock_json = response.json()
    return version_lock_json['versionLock']

def add_to_prestage(serial, prestage_version_lock, auth_token, ios_device_type):
    url = f'{jamf_pro_url}/api/v2/mobile-device-prestages/{ios_device_type}/scope'

    payload = { 
        "serialNumbers": [serial],
        "versionLock": prestage_version_lock
    }
    headers = {
        "authorization": f'Bearer {auth_token}',
        "accept": "application/json",
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response.text)

def lambda_handler(event, context):
    try:
        jamf_token = create_jamf_token(jamf_pro_url, jamf_pro_username, jamf_pro_password)
        
        json_data = json.loads(event['body'])
        device_model = json_data['event']['model'].lower()
        serial_number = json_data['event']['serialNumber']
        
        print(f'Model: {device_model}, Serial:{serial_number}')
        
        if "iphone" in device_model:
            device_type = 2
            print("Device is an iPhone, attempting to add to iPhone prestage.")
        else:
            print("Device is not an iPhone, checking if it is an iPad.")
            if "ipad" in device_model:
                device_type = 1
                print("Device is an iPad, attempting to add to iPad prestage.")
            else:
                print("Device is not an iPhone or an iPad, exiting.")
                return {
                    'statusCode': 400,
                    'body': json.dumps('Device is not supported.')
                }

        version_lock = get_prestage_version_lock(jamf_token, device_type)
        add_to_prestage(serial_number, version_lock, jamf_token, device_type)

        return {
            'statusCode': 200,
            'body': json.dumps('Device added to prestage successfully.')
        }
    
    except Exception as e:
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps('Unknown error.')
        }
