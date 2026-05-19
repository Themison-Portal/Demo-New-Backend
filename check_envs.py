import json
import os

try:
    with open('envs.json') as f:
        data = json.load(f)
        # Handle different potential JSON structures from gcloud
        if isinstance(data, list):
            envs = data[0]['spec']['template']['spec']['containers'][0]['env']
        else:
            envs = data['spec']['template']['spec']['containers'][0]['env']
            
        for e in envs:
            name = e['name']
            val = e['value']
            print(f"{name}: len={len(val)} repr={repr(val)}")
except Exception as e:
    print(f"Error: {e}")
