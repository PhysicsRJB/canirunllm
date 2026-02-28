from flask import Flask, jsonify, request
import psutil
import json
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load LLM hardware requirements
LLM_MODELS_PATH = os.path.join(os.path.dirname(__file__), 'llm_models.json')
if os.path.exists(LLM_MODELS_PATH):
    with open(LLM_MODELS_PATH, 'r') as f:
        LLM_MODELS = json.load(f)
else:
    LLM_MODELS = {}


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
    req = LLM_MODELS.get(llm_name)
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

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
