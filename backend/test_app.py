import json
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_hardware_endpoint(client):
    resp = client.get('/api/hardware')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'cpu' in data
    assert 'ram' in data
    assert 'gpus' in data

def test_compatibility_endpoint(client):
    resp = client.get('/api/check_compatibility?llm=gpt2_small')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['llm'] == 'gpt2_small'
    assert 'compatibility' in data
    assert data['compatibility']['status'] in ('compatible', 'incompatible', 'unknown_llm')