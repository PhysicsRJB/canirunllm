document.addEventListener('DOMContentLoaded', () => {
    const hardwareInfoEl = document.getElementById('hardware-info');
    const resultEl = document.getElementById('result');
    const llmSelect = document.getElementById('llm-select');
    const checkBtn = document.getElementById('check-btn');

    // Load hardware info on page load
    fetch('http://localhost:5000/api/hardware')
        .then(response => response.json())
        .then(data => {
            hardwareInfoEl.textContent = JSON.stringify(data, null, 2);
        })
        .catch(err => {
            hardwareInfoEl.textContent = 'Failed to load hardware info: ' + err;
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
});
