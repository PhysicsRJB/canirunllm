import requests, json, sys
url = 'http://127.0.0.1:5000/api/models/filter'
params = {'min_ram': 0, 'min_vram': 0}
resp = requests.get(url, params=params)
print('Status:', resp.status_code)
print('Headers:', resp.headers.get('Content-Type'))
print('Body:', resp.text[:500])
