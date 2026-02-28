document.addEventListener('DOMContentLoaded', () => {
    const hardwareInfoEl = document.getElementById('hardware-info');
    const resultEl = document.getElementById('result');
    const llmSelect = document.getElementById('llm-select');
    const checkBtn = document.getElementById('check-btn');

    // Load hardware info on page load
    fetch('http://localhost:5000/api/hardware')
        .then(response => response.json())
        .then(data => {
            // Store hardware info globally for later compatibility checks
            window.detectedHardware = data;
            // Build a simple HTML table for hardware info
            const {cpu, ram, gpus} = data;
            let html = `<table border="1" cellpadding="4" cellspacing="0"><tr><th colspan="2">Detected Hardware</th></tr>`;
            html += `<tr><td>CPU</td><td>${cpu.model} (${cpu.cores} cores, ${cpu.logical_cores} logical)</td></tr>`;
            html += `<tr><td>RAM</td><td>${ram.total_gb} GB</td></tr>`;
            if (gpus && gpus.length > 0) {
                html += `<tr><td>GPU</td><td>${gpus[0].name} (${gpus[0].total_vram_gb} GB VRAM)</td></tr>`;
            } else {
                html += `<tr><td>GPU</td><td>None detected</td></tr>`;
            }
            html += `</table>`;
            hardwareInfoEl.innerHTML = html;
        })
        .catch(err => {
            hardwareInfoEl.textContent = 'Failed to load hardware info: ' + err;
        });
    // Load model list for the dropdown (client-side from static JSON, only models with known requirements and compatible with detected hardware)
    fetch('http://localhost:5000/static/models_info.json')
        .then(r => r.json())
        .then(models => {
            // Ensure hardware info is available
            const hardware = window.detectedHardware;
            if (!hardware) {
                console.warn('Hardware info not loaded yet; showing all known models.');
                // Fallback to known models without compatibility filtering
                const knownFallback = Object.entries(models).filter(([id, info]) =>
                    info.min_ram_gb > 0 || info.min_vram_gb > 0 || info.gpu_required
                );
                const entriesFallback = knownFallback.sort((a, b) => {
                    const aScore = a[1].min_ram_gb + a[1].min_vram_gb;
                    const bScore = b[1].min_ram_gb + b[1].min_vram_gb;
                    return bScore - aScore;
                });
                window.modelEntries = entriesFallback;
                populateDropdown(entriesFallback);
                return;
            }
            const totalRam = hardware.ram.total_gb;
            const gpu = hardware.gpus && hardware.gpus.length > 0 ? hardware.gpus[0] : null;
            const totalVram = gpu ? gpu.total_vram_gb : 0;
            const hasGpu = !!gpu;

            // Filter models that have known hardware requirements and are compatible with the detected hardware
            const compatible = Object.entries(models).filter(([id, info]) => {
                const meetsRam = info.min_ram_gb <= totalRam;
                const meetsVram = info.min_vram_gb <= totalVram;
                const gpuOk = !info.gpu_required || hasGpu;
                const knownReq = info.min_ram_gb > 0 || info.min_vram_gb > 0 || info.gpu_required;
                return knownReq && meetsRam && meetsVram && gpuOk;
            });
            // Sort descending by total resource requirement (RAM + VRAM)
            const entries = compatible.sort((a, b) => {
                const aScore = a[1].min_ram_gb + a[1].min_vram_gb;
                const bScore = b[1].min_ram_gb + b[1].min_vram_gb;
                return bScore - aScore;
            });
            // Store entries for later search filtering
            window.modelEntries = entries;
            populateDropdown(entries);
        })
        .catch(err => console.error('Failed to load model list for select', err));

    // Helper to populate the dropdown (keeps placeholder)
    function populateDropdown(entries) {
        // Reset dropdown to only placeholder
        llmSelect.innerHTML = '<option value="" disabled selected>Select a model</option>';
        entries.forEach(([id, info]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            llmSelect.appendChild(opt);
        });
    }

    // Search box filtering
    const searchBox = document.getElementById('model-search');
    searchBox.addEventListener('input', () => {
        const term = searchBox.value.trim().toLowerCase();
        const filtered = window.modelEntries.filter(([id]) => id.toLowerCase().includes(term));
        populateDropdown(filtered);
    });

    checkBtn.addEventListener('click', () => {
        const llm = llmSelect.value;
        resultEl.textContent = 'Checking...';
        fetch(`http://localhost:5000/api/check_compatibility?llm=${encodeURIComponent(llm)}`)
            .then(response => response.json())
            .then(data => {
                const comp = data.compatibility;
                resultEl.textContent = `${comp.status.toUpperCase()}: ${comp.message}`;
            })
            .catch(err => {
                resultEl.textContent = 'Error checking compatibility: ' + err;
            });
    });
    // Load compatible models based on detected hardware (client-side filtering)
    const modelsBtn = document.getElementById('load-models-btn');
    const modelsListEl = document.getElementById('models-list');
    modelsBtn.addEventListener('click', () => {
        const hardware = JSON.parse(hardwareInfoEl.textContent);
        const minRam = hardware.ram.total_gb;
        const minVram = hardware.gpus.length > 0 ? hardware.gpus[0].total_vram_gb : 0;
        modelsListEl.textContent = 'Loading models...';
        fetch('http://localhost:5000/static/models_info.json')
            .then(r => r.json())
            .then(data => {
                let entries = Object.entries(data).filter(([id, info]) =>
                    info.min_ram_gb <= minRam && info.min_vram_gb <= minVram);
                // Sort descending by total resource requirement (RAM + VRAM)
                entries.sort((a, b) => {
                    const aScore = a[1].min_ram_gb + a[1].min_vram_gb;
                    const bScore = b[1].min_ram_gb + b[1].min_vram_gb;
                    return bScore - aScore;
                });
                if (entries.length === 0) {
                    modelsListEl.textContent = 'No compatible models found.';
                } else {
                    const lines = entries.map(([id, info]) => `${id}: RAM ${info.min_ram_gb}GB, VRAM ${info.min_vram_gb}GB, GPU required: ${info.gpu_required}`);
                    modelsListEl.textContent = lines.join('\n');
                }
            })
            .catch(err => {
                modelsListEl.textContent = 'Error loading models: ' + err;
            });
    });
});
