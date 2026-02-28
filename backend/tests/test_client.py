from ..app import app
client = app.test_client()
resp = client.get('/api/models')
print('status', resp.status_code)
print('data', resp.get_data(as_text=True)[:200])
