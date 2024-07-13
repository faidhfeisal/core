import requests


NODE_JS_SERVICE_URL = 'http://localhost:3000'


def publish_to_streamr(stream_id, data):
    url = f'{NODE_JS_SERVICE_URL}/publish'
    response = requests.post(url, json={'streamId': stream_id, 'data': data})
    response.raise_for_status()

def subscribe_to_streamr(stream_id):
    url = f'{NODE_JS_SERVICE_URL}/subscribe'
    response = requests.post(url, json={'streamId': stream_id})
    response.raise_for_status()
    return response.json()['subscriptionId']
