import requests, json
url = 'http://127.0.0.1:5000/api/models'
resp = requests.get(url)
print('status', resp.status_code)
print('text', resp.text[:200])
