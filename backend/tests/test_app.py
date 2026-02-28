import json
import pytest
from ..app import app, detect_hardware, check_compatibility, MODELS_INFO, LLM_MODELS

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_hardware_endpoint(client):
    resp = client.get('/api/hardware')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'cpu' in data and 'ram' in data and 'gpus' in data


def test_check_compatibility_known(client):
    # Use a model from LLM_MODELS which has known requirements
    llm = list(LLM_MODELS.keys())[0]
    resp = client.get(f'/api/check_compatibility?llm={llm}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['llm'] == llm
    assert data['compatibility']['status'] in ('compatible', 'incompatible')


def test_check_compatibility_unknown(client):
    resp = client.get('/api/check_compatibility?llm=nonexistent/model')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['compatibility']['status'] == 'unknown_llm'


def test_models_endpoint(client):
    resp = client.get('/api/models')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # Ensure at least one model entry exists
    assert len(data) > 0


def test_models_filter_endpoint(client):
    # With low thresholds, should return many models
    resp = client.get('/api/models/filter?min_ram=0&min_vram=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # All models should be returned (since sample data has 0 requirements)
    assert len(data) == len(MODELS_INFO)


def test_models_filter_higher_ram(client):
    # Set high RAM requirement that exceeds sample models (all have 0)
    resp = client.get('/api/models/filter?min_ram=20&min_vram=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert len(data) == len(MODELS_INFO)

def test_models_compatible_endpoint(client):
    resp = client.get('/api/models/compatible')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # Ensure returned models are a subset of known models
    for model_id in data:
        assert model_id in MODELS_INFO


def test_check_compatibility_uses_models_info():
    # Pick a model that is not in LLM_MODELS but is in MODELS_INFO
    # Ensure MODELS_INFO contains at least one entry not in LLM_MODELS
    extra_models = [mid for mid in MODELS_INFO if mid not in LLM_MODELS]
    if not extra_models:
        pytest.skip('No extra models to test')
    model_id = extra_models[0]
    hardware = detect_hardware()
    result = check_compatibility(model_id, hardware)
    # Since sample models have 0 requirements, should be compatible
    assert result['status'] == 'compatible'
