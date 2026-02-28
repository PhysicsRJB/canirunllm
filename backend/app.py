from flask import Flask, jsonify, request
import psutil
import json
import os
from huggingface_hub import HfApi
from flask_cors import CORS

app = Flask(__name__)

@app.route('/test')
def test_route():
    return jsonify({'msg': 'test ok'})

@app.route('/list_routes')
def list_routes():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])
print('App started')

# @app.errorhandler(404)
def not_found(e):
    print('404 handler invoked for', request.path, flush=True)
    return jsonify({'error': 'Not found'}), 404

@app.route('/debug/all_routes')
def debug_all_routes():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])
@app.route('/debug/hello')
def debug_hello():
    return jsonify({'message': 'hello'})
CORS(app)

@app.route('/info')
def info_route():
    return jsonify({'status': 'ok'})

@app.errorhandler(404)
def not_found(e):
    print('404 handler invoked for', request.path, flush=True)
    return jsonify({'error': 'Not found'}), 404
@app.before_request
def log_path():
    print('Incoming request:', request.path, flush=True)

@app.route('/ping')
def ping():
    return 'pong'

# Load LLM hardware requirements
LLM_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'llm_models.json')
if os.path.exists(LLM_MODELS_PATH):
    with open(LLM_MODELS_PATH, 'r') as f:
        LLM_MODELS = json.load(f)
else:
    LLM_MODELS = {}

# Load or fetch model hardware requirements from HuggingFace
# The models_info.json file is refreshed at most once per day. If the file does not exist
# or is older than the current day, we fetch the top‑500 most‑downloaded models from
# HuggingFace Hub, compute their hardware requirements, and store the result.
from datetime import datetime, timedelta
MODELS_INFO_PATH = os.path.join(os.path.dirname(__file__), 'static', 'models_info.json')
print('Loading models info from', MODELS_INFO_PATH)

def load_models_info():
    # If the file exists and was modified today, reuse it.
    if os.path.exists(MODELS_INFO_PATH):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(MODELS_INFO_PATH))
            if mtime.date() == datetime.now().date():
                with open(MODELS_INFO_PATH, 'r') as f:
                    data = json.load(f)
                print('Loaded MODELS_INFO keys (cached):', list(data.keys()))
                return data
        except Exception:
            # If any error occurs, fall back to re‑fetching.
            pass
    # Otherwise, fetch the latest top‑500 models.
    api = HfApi()
    models = list(api.list_models(sort="downloads", limit=500))
    print('Number of models fetched from HuggingFace:', len(models))
    info_dict = {}
    for model in models:
        model_id = model.modelId
        try:
            info = api.model_info(model_id)
            # Sum sizes of model files (bin, safetensors, pt)
            total_bytes = sum(
                (sibling.size or 0) for sibling in info.siblings
                if sibling.rfilename.endswith(('.bin', '.safetensors', '.pt'))
            )
            # Estimate RAM requirement (approx double the model size for loading in FP16)
            min_ram_gb = int((total_bytes / (1024**3)) * 2 + 0.999)  # ceil
            gpu_required = total_bytes > 2 * 1024**3  # >2GB
            min_vram_gb = min_ram_gb if gpu_required else 0
            info_dict[model_id] = {
                "min_ram_gb": min_ram_gb,
                "min_vram_gb": min_vram_gb,
                "gpu_required": gpu_required
            }
        except Exception:
            # If we cannot fetch model info, still add the model with default (zero) requirements
            info_dict[model_id] = {
                "min_ram_gb": 0,
                "min_vram_gb": 0,
                "gpu_required": False
            }
    # Save for future use
    with open(MODELS_INFO_PATH, 'w') as f:
        json.dump(info_dict, f, indent=2)
    print('Fetched and saved MODELS_INFO keys:', list(info_dict.keys()))
    return info_dict

# Load the model info (cached or fresh)
MODELS_INFO = load_models_info()

def get_cpu_info():
    # psutil does not provide model name directly; we can use platform.uname on Windows
    try:
        import platform
        cpu = platform.uname().processor
    except Exception:
        cpu = 'Unknown'
    cores = psutil.cpu_count(logical=False) or 0
    logical = psutil.cpu_count(logical=True) or 0
    return {
        'model': cpu,
        'cores': cores,
        'logical_cores': logical
    }

def get_ram_info():
    mem = psutil.virtual_memory()
    # Return GB
    return {
        'total_gb': round(mem.total / (1024**3), 2)
    }

def get_gpu_info():
    # Use GPUtil if available; otherwise return empty list
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        gpu_list = []
        for gpu in gpus:
            gpu_list.append({
                'name': gpu.name,
                'total_vram_gb': round(gpu.memoryTotal / 1024, 2)
            })
        return gpu_list
    except Exception:
        return []

def detect_hardware():
    return {
        'cpu': get_cpu_info(),
        'ram': get_ram_info(),
        'gpus': get_gpu_info()
    }

def check_compatibility(llm_name, hardware):
    req = MODELS_INFO.get(llm_name) or LLM_MODELS.get(llm_name)
    if not req:
        return {
            'status': 'unknown_llm',
            'message': f'No hardware requirements defined for {llm_name}'
        }
    # Check RAM
    ram_ok = hardware['ram']['total_gb'] >= req.get('min_ram_gb', 0)
    # Check GPU if required
    gpu_required = req.get('gpu_required', False)
    gpu_ok = True
    gpu_reason = ''
    if gpu_required:
        if not hardware['gpus']:
            gpu_ok = False
            gpu_reason = 'No GPU detected'
        else:
            # Assume first GPU for simplicity
            gpu = hardware['gpus'][0]
            gpu_ok = gpu['total_vram_gb'] >= req.get('min_vram_gb', 0)
            if not gpu_ok:
                gpu_reason = f"GPU VRAM {gpu['total_vram_gb']}GB insufficient (requires {req.get('min_vram_gb', 0)}GB)"
    overall_ok = ram_ok and gpu_ok
    if overall_ok:
        return {
            'status': 'compatible',
            'message': f'{llm_name} can run on this machine.'
        }
    else:
        reasons = []
        if not ram_ok:
            reasons.append(f"RAM {hardware['ram']['total_gb']}GB insufficient (requires {req.get('min_ram_gb', 0)}GB)")
        if not gpu_ok:
            reasons.append(gpu_reason)
        return {
            'status': 'incompatible',
            'message': f'{llm_name} cannot run on this machine: ' + '; '.join(reasons)
        }

@app.route('/api/hardware')
def api_hardware():
    print('api_hardware called')
    return jsonify(detect_hardware())

@app.route('/api/check_compatibility')
def api_check_compatibility():
    llm = request.args.get('llm')
    if not llm:
        return jsonify({'error': 'Missing llm query parameter'}), 400
    hardware = detect_hardware()
    result = check_compatibility(llm, hardware)
    response = {
        'hardware': hardware,
        'llm': llm,
        'compatibility': result
    }
    return jsonify(response)

@app.route('/api/models')
def api_models():
    print('api_models called')
    # Return all models with their requirements
    return jsonify(MODELS_INFO)

@app.route('/api/models/filter')
def api_models_filter():
    # Filter based on hardware constraints passed as query params
    try:
        min_ram = float(request.args.get('min_ram', 0))
        min_vram = float(request.args.get('min_vram', 0))
    except ValueError:
        return jsonify({'error': 'Invalid numeric query parameter'}), 400
    filtered = {
        model_id: info for model_id, info in MODELS_INFO.items()
        if info.get('min_ram_gb', 0) <= min_ram and info.get('min_vram_gb', 0) <= min_vram
    }
    return jsonify(filtered)

@app.route('/api/models/compatible')
def api_models_compatible():
    """Return all models from the cached top‑500 list that are compatible with the detected hardware."""
    hardware = detect_hardware()
    compatible = {}
    for model_id, req in MODELS_INFO.items():
        result = check_compatibility(model_id, hardware)
        if result.get('status') == 'compatible':
            compatible[model_id] = req
    return jsonify(compatible)

# @app.errorhandler(404)

def debug_all_routes():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])

@app.route('/debug/all_routes')
def debug_all_routes_route():
    return debug_all_routes()
def not_found(e):
    print('404 handler invoked for', request.path, flush=True)
    return jsonify({'error': 'Not found'}), 404

# Debug route removed to avoid duplicate endpoint

@app.route('/debug/models_info')

def get_model(model):
    return jsonify(MODELS_INFO.get(model, {}))
def debug_models_info():
    return jsonify(MODELS_INFO)

@app.route('/debug/get_model/<path:model>')
def debug_get_model(model):
    return jsonify(MODELS_INFO.get(model, {}))

@app.route('/debug/routes')
def debug_routes():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])
@app.route('/debug/models_path')
def debug_models_path():
    return jsonify({'path': MODELS_INFO_PATH})

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
