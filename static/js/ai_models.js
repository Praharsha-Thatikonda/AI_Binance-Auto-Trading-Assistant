// API Key Saving
window.saveAIKeyPage = async function () {
    const key = document.getElementById('api_key_input').value;
    const provider = document.getElementById('ai-provider').value;
    const statusMsg = document.getElementById('config-status-msg');

    if (!key) {
        showStatus(statusMsg, "Please enter a valid API key.", "error");
        return;
    }

    try {
        const payload = {
            provider: provider,
            api_key: key,
            model_name: provider === 'google' ? 'gemini-pro' : (provider === 'openai' ? 'gpt-4' : 'claude-3')
        };

        const res = await fetch('/ai/config/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            showStatus(statusMsg, data.message, "success");
            document.getElementById('api_key_input').value = "";
        } else {
            showStatus(statusMsg, data.detail || "Failed to save API Key.", "error");
        }
    } catch (e) {
        console.error(e);
        showStatus(statusMsg, "Error connecting to server.", "error");
    }
}

window.updateProviderFields = function () {
    const provider = document.getElementById('ai-provider').value;
    const helpText = document.getElementById('key-help-text');

    if (provider === 'google') {
        helpText.textContent = "Required for Gemini Pro analysis.";
    } else if (provider === 'openai') {
        helpText.textContent = "Required for GPT-4 analysis.";
    } else if (provider === 'anthropic') {
        helpText.textContent = "Required for Claude 3 analysis.";
    }
}

// Test Connection
window.testConnection = async function () {
    const provider = document.getElementById('ai-provider').value;
    const statusMsg = document.getElementById('config-status-msg');
    showStatus(statusMsg, `Testing connection to ${provider.toUpperCase()}...`, "success");

    try {
        const res = await fetch('/ai/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider: provider })
        });
        const data = await res.json();

        if (res.ok) {
            showStatus(statusMsg, data.message, "success");
        } else {
            showStatus(statusMsg, data.detail || "Failed to test connection.", "error");
        }
    } catch (e) {
        console.error(e);
        showStatus(statusMsg, "Error connecting to server.", "error");
    }
}

// Local Model Configuration
window.saveLocalConfig = async function () {
    const path = document.getElementById('local_model_path').value;
    const device = document.getElementById('compute-device').value;
    const statusMsg = document.getElementById('config-status-msg');

    if (!path) {
        showStatus(statusMsg, "Please enter a valid path.", "error");
        return;
    }

    try {
        const res = await fetch('/ai/local-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ local_model_path: path, compute_device: device })
        });

        if (res.ok) {
            showStatus(statusMsg, `Path set to: ${path} [Device: ${device.toUpperCase()}]`, "success");
        } else {
            showStatus(statusMsg, "Failed to save local config", "error");
        }
    } catch (e) {
        showStatus(statusMsg, "Error saving local config", "error");
    }
}

// Global Parameters Configuration
window.saveGlobalParams = async function () {
    const temp = parseFloat(document.getElementById('global-temp').value);
    const tokens = parseInt(document.getElementById('global-tokens').value);
    const prompt = document.getElementById('global-prompt').value;
    const statusMsg = document.getElementById('config-status-msg');

    try {
        const res = await fetch('/ai/global-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                temperature: temp,
                max_output_tokens: tokens,
                system_prompt: prompt
            })
        });

        const data = await res.json();

        if (res.ok) {
            showStatus(statusMsg, data.message, "success");
        } else {
            showStatus(statusMsg, "Failed to save global parameters", "error");
        }
    } catch (e) {
        console.error(e);
        showStatus(statusMsg, "Error saving global parameters", "error");
    }
}

// Load Configuration on Page Load
window.loadConfiguration = async function () {
    try {
        // Use AppCore for caching if available, otherwise fallback to fetch
        let res;
        if (typeof AppCore !== 'undefined') {
            res = await AppCore.fetchWithCache('/ai/config', { method: 'GET' }, 60);
        } else {
            res = await fetch('/ai/config');
        }

        const config = await res.json();

        // Store keys globally or just populate current provider field
        window.apiKeys = {
            google: config.google_key,
            openai: config.openai_key,
            anthropic: config.anthropic_key
        };

        // Populate Provider Field
        updateProviderFields(); // Will set help text
        const provider = document.getElementById('ai-provider').value;
        if (window.apiKeys[provider]) {
            document.getElementById('api_key_input').value = window.apiKeys[provider];
        }

        // Populate Local Config
        if (config.local_path) document.getElementById('local_model_path').value = config.local_path;
        if (config.compute_device) document.getElementById('compute-device').value = config.compute_device;

        // Populate Global Params
        if (config.global_params) {
            document.getElementById('global-temp').value = config.global_params.temperature;
            document.getElementById('global-tokens').value = config.global_params.max_tokens;
            document.getElementById('global-prompt').value = config.global_params.system_prompt;
        }

    } catch (e) {
        console.error("Error loading configuration:", e);
    }
}

// Hook into provider change to update input
const originalUpdateProvider = window.updateProviderFields;
window.updateProviderFields = function () {
    originalUpdateProvider();
    const provider = document.getElementById('ai-provider').value;
    if (window.apiKeys && window.apiKeys[provider]) {
        document.getElementById('api_key_input').value = window.apiKeys[provider];
    } else {
        document.getElementById('api_key_input').value = "";
    }
}

// Helper for status messages
function showStatus(element, message, type) {
    if (!element) return; // Guard clause
    element.textContent = message;
    element.style.display = "block";
    if (type === "success") {
        element.style.background = "rgba(16, 185, 129, 0.2)";
        element.style.color = "#34d399";
    } else {
        element.style.background = "rgba(239, 68, 68, 0.2)";
        element.style.color = "#f87171";
    }
    setTimeout(() => {
        element.style.display = "none";
    }, 4000);
}

// Model Management Functions
window.triggerModelImport = function () {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async e => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async event => {
            try {
                const data = JSON.parse(event.target.result);
                const items = Array.isArray(data) ? data : [data];
                let successCount = 0;

                for (const item of items) {
                    if (!item.name) continue;

                    const payload = {
                        name: item.name,
                        architecture: item.settings?.architecture || 'custom',
                        purpose: item.settings?.purpose || 'regression',
                        features: item.settings?.features || ['close']
                    };

                    const res = await fetch('/ai/models/import', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) successCount++;
                }

                alert(`Imported ${successCount} models successfully.`);
                loadActiveModels();
            } catch (err) {
                console.error(err);
                alert("Failed to parse or import file.");
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

window.triggerExport = function () {
    window.location.href = '/ai/models/export';
}

window.activateModel = function (modelId) {
    toggleModel(modelId, true);
}

window.exportModel = function (modelId) {
    window.location.href = `/ai/models/${modelId}/export`;
}

// Toggle Model Function
window.toggleModel = async function (modelId, isChecked) {
    const statusMsg = document.getElementById('config-status-msg');

    // Update UI text next to toggle
    const toggle = event.target;
    const statusText = toggle.parentElement.previousElementSibling;
    if (statusText) {
        statusText.textContent = isChecked ? "● Active" : "● Stopped";
        statusText.style.color = isChecked ? "#10b981" : "var(--text-secondary)";
    }

    // Update Active Agents Count
    const countEl = document.getElementById('active-agents-count');
    if (countEl) {
        let current = parseInt(countEl.textContent);
        if (isChecked) current++; else current--;
        if (current < 0) current = 0;
        countEl.textContent = current;
    }

    try {
        const res = await fetch('/ai/models/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_id: modelId, is_active: isChecked })
        });
        const data = await res.json();

        if (res.ok) {
            if (statusMsg) showStatus(statusMsg, data.message, "success");
        } else {
            if (statusMsg) showStatus(statusMsg, "Failed to update model status", "error");
            // Revert toggle if failed?
            toggle.checked = !isChecked;
        }
    } catch (e) {
        console.error(e);
        if (statusMsg) showStatus(statusMsg, "Network error toggling model", "error");
        toggle.checked = !isChecked;
    }
}

// Training Functions
window.createModel = async function () {
    const name = document.getElementById('new-model-name').value;
    const arch = document.getElementById('model-arch').value;
    const purpose = document.getElementById('model-purpose').value;

    // Get checked features
    const features = [];
    document.querySelectorAll('.features-grid input:checked').forEach(cb => features.push(cb.value));

    if (!name) {
        alert("Please enter a model name.");
        return;
    }

    try {
        const res = await fetch('/ai/models/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                architecture: arch,
                purpose: purpose,
                features: features
            })
        });

        const data = await res.json();

        if (res.ok) {
            alert(data.message);
            document.getElementById('new-model-name').value = "";
            populateTrainingDropdowns(); // Refresh dropdown
        } else {
            alert("Error: " + data.detail);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to create model.");
    }
}

window.populateTrainingDropdowns = async function () {
    const modelSelect = document.getElementById('train-model-select');
    const datasetSelect = document.getElementById('train-dataset-select');

    if (!modelSelect || !datasetSelect) return;

    // Load Models (Local only for training usually, but let's load all active local ones)
    try {
        const res = await fetch('/ai/models');
        const data = await res.json();
        const localModels = data.local; // Only train local models

        modelSelect.innerHTML = '<option value="" disabled selected>Select a model...</option>';
        localModels.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name; // Use name as ID for now based on backend logic
            opt.text = m.name;
            modelSelect.add(opt);
        });
    } catch (e) { console.error("Error loading models for training", e); }

    // Load Datasets
    try {
        const res = await fetch('/ai/datasets');
        const datasets = await res.json();

        datasetSelect.innerHTML = '<option value="" disabled selected>Select a dataset...</option>';
        datasets.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.text = d.name;
            datasetSelect.add(opt);
        });
    } catch (e) { console.error("Error loading datasets for training", e); }
}

window.startTraining = async function () {
    const progressDiv = document.getElementById('training-progress');
    const pBar = document.getElementById('p-bar');
    const pText = document.getElementById('p-text');
    const pPercent = document.getElementById('p-text-percent');
    const logs = document.getElementById('training-logs');

    // Get Hyperparams
    const modelName = document.getElementById('train-model-select').value;
    const datasetId = document.getElementById('train-dataset-select').value;
    const epochs = parseInt(document.getElementById('epochs').value);
    const batchSize = parseInt(document.getElementById('batch-size').value);
    const lr = parseFloat(document.getElementById('learning-rate').value);
    const optimizer = document.getElementById('optimizer').value;

    if (!modelName || !datasetId) {
        alert("Please select both a model and a dataset.");
        return;
    }

    progressDiv.style.display = "block";
    pBar.style.width = "0%";
    pPercent.textContent = "0%";
    pText.textContent = "Initializing training environment...";
    logs.innerHTML = `<div class="log-line">> Initializing training run for ${modelName}...</div>`;

    try {
        // Start Training
        const res = await fetch('/ai/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model_name: modelName,
                dataset_id: parseInt(datasetId),
                epochs: epochs,
                batch_size: batchSize,
                learning_rate: lr,
                optimizer: optimizer
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert("Error: " + err.detail);
            return;
        }

        // Poll Status
        const interval = setInterval(async () => {
            const statusRes = await fetch('/ai/train/status');
            const state = await statusRes.json();

            pBar.style.width = `${state.progress}%`;
            pPercent.textContent = `${state.progress}%`;
            pText.textContent = `Training: Epoch ${state.current_epoch}/${state.total_epochs}`;

            // Append new logs
            logs.innerHTML = "";
            state.logs.forEach(log => {
                const div = document.createElement('div');
                div.className = 'log-line';
                div.textContent = "> " + log;
                logs.appendChild(div);
            });
            logs.scrollTop = logs.scrollHeight;

            if (state.status === 'completed') {
                clearInterval(interval);
                pText.textContent = "Training Complete!";
                pBar.style.background = "#10b981";
                alert("Training finished successfully.");
            }
        }, 1000);

    } catch (e) {
        console.error(e);
        alert("Failed to start training.");
    }
}

window.toggleConfigMode = function () {
    const isAdvanced = document.getElementById('config-mode-toggle').checked;
    const localEnv = document.querySelector('.grid-2-col > div:nth-child(2)'); // Local Environment column
    const globalParams = document.getElementById('global-params');
    const advancedTraining = document.querySelector('.advanced-options');

    // Grid Layout Adjustment
    const grid = document.querySelector('.grid-2-col');

    if (isAdvanced) {
        if (localEnv) localEnv.style.display = 'block';
        if (globalParams) globalParams.style.display = 'block';
        if (grid) grid.style.gridTemplateColumns = '1fr 1fr'; // 2 columns (Cloud + Local)
    } else {
        if (localEnv) localEnv.style.display = 'none';
        if (globalParams) globalParams.style.display = 'none';
        if (grid) grid.style.gridTemplateColumns = '1fr'; // 1 column (Cloud only)
    }

    if (advancedTraining) {
        advancedTraining.style.display = isAdvanced ? 'grid' : 'none';
    }
}

// Tab Switching
window.switchTab = function (tab) {
    const modelsTab = document.getElementById('models-tab');
    const datasetsTab = document.getElementById('datasets-tab');
    const tabModelsBtn = document.querySelector('.tab-btn:nth-child(1)');
    const tabDatasetsBtn = document.querySelector('.tab-btn:nth-child(2)');

    if (tab === 'models') {
        modelsTab.style.display = 'block';
        datasetsTab.style.display = 'none';
        tabModelsBtn.classList.add('active');
        tabDatasetsBtn.classList.remove('active');
        loadActiveModels();
    } else {
        modelsTab.style.display = 'none';
        datasetsTab.style.display = 'block';
        tabModelsBtn.classList.remove('active');
        tabDatasetsBtn.classList.add('active');
        loadDatasets();
    }
}

// Load Active Models
window.loadActiveModels = async function () {
    const grid = document.getElementById('active-models-grid');
    if (!grid) return;

    try {
        const res = await fetch('/ai/models');
        const data = await res.json();

        // Flatten server and local models
        const allModels = [...data.server, ...data.local];

        // Update Active Agents Count
        const activeCount = allModels.filter(m => m.status === 'active').length;
        const countEl = document.getElementById('active-agents-count');
        if (countEl) countEl.textContent = activeCount;

        if (allModels.length === 0) {
            grid.innerHTML = '<p style="grid-column: span 2; text-align: center; color: var(--text-secondary);">No active models configured.</p>';
            return;
        }

        grid.innerHTML = allModels.map(model => `
            <div class="model-card ${model.status === 'active' ? 'active' : ''}">
                <div class="model-header">
                    <h3 class="model-name">${model.name}</h3>
                    <span class="model-badge badge-${model.provider === 'local' ? 'local' : 'server'}">${model.provider.toUpperCase()}</span>
                </div>
                <p class="model-desc">Status: ${model.status}</p>
                <div class="model-actions" style="justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <span class="status-text" style="color: ${model.status === 'active' ? '#10b981' : 'var(--text-secondary)'}; font-size: 0.8rem;">
                        ● ${model.status === 'active' ? 'Active' : 'Stopped'}
                    </span>
                    <label class="toggle">
                        <input type="checkbox" ${model.status === 'active' ? 'checked' : ''} onchange="toggleModel('${model.id}', this.checked)">
                        <span class="slider"></span>
                    </label>
                    <button onclick="exportModel('${model.name}')" style="background: none; border: none; color: #3b82f6; cursor: pointer; margin-left: 0.5rem;" title="Export Config">⬇️</button>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error(e);
        grid.innerHTML = '<p style="grid-column: span 2; text-align: center; color: #ef4444;">Failed to load models.</p>';
    }
}

// Load Datasets
window.loadDatasets = async function () {
    const tbody = document.getElementById('datasets-list');
    if (!tbody) return;

    try {
        const res = await fetch('/ai/datasets');
        const datasets = await res.json();

        if (datasets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: var(--text-secondary);">No datasets found.</td></tr>';
            return;
        }

        tbody.innerHTML = datasets.map(ds => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 0.8rem 0.5rem;">${ds.name}</td>
                <td style="padding: 0.8rem 0.5rem;">${ds.type.toUpperCase()}</td>
                <td style="padding: 0.8rem 0.5rem;">${ds.size}</td>
                <td style="padding: 0.8rem 0.5rem;">${ds.created_at}</td>
                <td style="padding: 0.8rem 0.5rem;">
                    <button onclick="deleteDataset(${ds.id})" style="background: none; border: none; color: #ef4444; cursor: pointer;">🗑️</button>
                    <button onclick="exportDataset(${ds.id})" style="background: none; border: none; color: #3b82f6; cursor: pointer; margin-left: 0.5rem;">⬇️</button>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: #ef4444;">Failed to load datasets.</td></tr>';
    }
}

window.triggerDatasetImport = async function () {
    const name = prompt("Enter dataset name:");
    if (!name) return;

    // Mock file selection for now
    const type = "csv"; // Default

    try {
        const res = await fetch('/ai/datasets/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, type: type, description: "Imported via UI" })
        });

        if (res.ok) {
            loadDatasets();
        } else {
            alert("Failed to import dataset.");
        }
    } catch (e) {
        alert("Error importing dataset.");
    }
}

window.deleteDataset = async function (id) {
    if (!confirm("Are you sure you want to delete this dataset?")) return;

    try {
        const res = await fetch(`/ai/datasets/${id}`, { method: 'DELETE' });
        if (res.ok) {
            loadDatasets();
        } else {
            alert("Failed to delete dataset.");
        }
    } catch (e) {
        alert("Error deleting dataset.");
    }
}

window.exportDataset = function (id) {
    window.location.href = `/ai/datasets/${id}/export`;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('config-mode-toggle')) {
        toggleConfigMode();
    }
    loadActiveModels();
    populateTrainingDropdowns();
    loadConfiguration();
});
