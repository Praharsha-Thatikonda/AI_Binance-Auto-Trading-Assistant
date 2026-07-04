document.addEventListener('DOMContentLoaded', () => {
    const startAiBtn = document.getElementById('start-ai-btn');
    const aiOutput = document.getElementById('ai-output');
    const aiStatus = document.getElementById('ai-status');
    const symbolSelect = document.getElementById('symbol');
    const geminiKeyInput = document.getElementById('gemini_key');
    const tradeAmountInput = document.getElementById('trade-amount');
    const tradeLog = document.getElementById('trade-log');

    // Output elements
    const techContent = document.getElementById('tech-content');
    const fundContent = document.getElementById('fund-content');
    const riskContent = document.getElementById('risk-content');
    const signalText = document.getElementById('signal-text');
    const confidenceText = document.getElementById('confidence-text');
    const reasoningContent = document.getElementById('reasoning-content');

    let autoTradeInterval = null;
    let isAnalyzing = false;

    function log(message) {
        const div = document.createElement('div');
        div.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        div.className = 'log-entry';
        if (tradeLog) tradeLog.prepend(div);
    }

    // --- New Trading Features ---

    // --- Tab Switching Logic ---
    window.switchMode = function (mode) {
        // Update Tabs
        const tabManual = document.getElementById('tab-manual');
        const tabAuto = document.getElementById('tab-auto');

        if (tabManual) {
            tabManual.style.borderBottom = mode === 'manual' ? '2px solid var(--accent-color)' : 'none';
            tabManual.style.color = mode === 'manual' ? 'white' : 'var(--text-secondary)';
            if (mode === 'manual') tabManual.classList.add('active'); else tabManual.classList.remove('active');
        }

        if (tabAuto) {
            tabAuto.style.borderBottom = mode === 'auto' ? '2px solid var(--accent-color)' : 'none';
            tabAuto.style.color = mode === 'auto' ? 'white' : 'var(--text-secondary)';
            if (mode === 'auto') tabAuto.classList.add('active'); else tabAuto.classList.remove('active');
        }

        // Show/Hide Panels
        const manualPanel = document.getElementById('manual-panel');
        const autoPanel = document.getElementById('auto-panel');

        if (manualPanel) manualPanel.style.display = mode === 'manual' ? 'block' : 'none';
        if (autoPanel) autoPanel.style.display = mode === 'auto' ? 'block' : 'none';
    }

    // Toggle Limit Price Input (Manual)
    window.togglePriceInput = function () {
        const type = document.getElementById('order-type').value;
        const priceGroup = document.getElementById('limit-price-group');
        if (priceGroup) {
            priceGroup.style.display = type === 'limit' ? 'grid' : 'none';
        }
    }

    // Helper to get active agents
    function getActiveAgents() {
        const agents = [];
        const checkboxes = document.querySelectorAll('#auto-panel input[type="checkbox"]');
        checkboxes.forEach(cb => {
            if (cb.id === 'auto-trade-toggle') return;
            if (cb.checked) {
                const text = cb.parentElement.textContent.trim().toLowerCase();
                if (text.includes('technical')) agents.push('technical');
                if (text.includes('sentiment')) agents.push('sentiment');
                if (text.includes('macro')) agents.push('macro');
                if (text.includes('whale')) agents.push('whale');
            }
        });
        return agents.join(',');
    }

    // Save AI Key & Config
    window.saveAIKey = async function () {
        const key = document.getElementById('gemini_key').value;
        const risk = document.getElementById('risk-level').value;
        const strategy = document.getElementById('strategy').value;
        const interval = document.getElementById('trading-interval').value;
        const maxLoss = document.getElementById('max-daily-loss').value;
        const targetProfit = document.getElementById('target-profit').value;
        const activeAgents = getActiveAgents();

        const payload = {
            gemini_api_key: key,
            risk_level: risk,
            trading_strategy: strategy,
            trading_interval: interval,
            max_daily_loss: maxLoss ? parseFloat(maxLoss) : null,
            target_profit: targetProfit ? parseFloat(targetProfit) : null,
            active_agents: activeAgents
        };

        try {
            const res = await fetch('/ai/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                if (key) {
                    document.getElementById('gemini_key').parentElement.style.display = 'none';
                    document.getElementById('key-status').style.display = 'block';
                }
                log("Configuration saved successfully.");
            } else {
                alert("Failed to save config");
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Execute Manual Trade
    window.executeManualTrade = async function (side) {
        const symbol = symbolSelect.value;
        const type = document.getElementById('order-type').value;
        const percentage = parseFloat(tradeAmountInput.value);
        const price = document.getElementById('limit-price').value;
        const stopLoss = document.getElementById('stop-loss').value;
        const takeProfit = document.getElementById('take-profit').value;

        log(`Executing MANUAL ${side.toUpperCase()} order for ${symbol}...`);

        try {
            const payload = {
                symbol: symbol,
                side: side,
                type: type,
                percentage: percentage,
                price: price ? parseFloat(price) : null,
                stop_loss: stopLoss ? parseFloat(stopLoss) : null,
                take_profit: takeProfit ? parseFloat(takeProfit) : null
            };

            const response = await fetch('/trading/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.status === 'success') {
                log(`SUCCESS: Order ${result.order_id} placed.`);
                fetchOrderHistory();
            } else {
                log(`FAILED: ${result.detail || 'Unknown error'}`);
            }
        } catch (e) {
            log(`System Error: ${e.message}`);
        }
    }

    // Fetch Order History
    async function fetchOrderHistory() {
        try {
            const res = await fetch('/trading/history');
            const orders = await res.json();
            const tbody = document.getElementById('order-history-body');
            if (!tbody) return;

            tbody.innerHTML = '';

            if (orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding: 1rem; text-align: center; color: var(--text-secondary);">No recent orders found.</td></tr>';
                return;
            }

            orders.forEach(order => {
                const date = new Date(order.timestamp).toLocaleString();
                const color = order.side === 'buy' ? '#10b981' : '#ef4444';
                const row = `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.75rem 0.5rem;">${date}</td>
                        <td style="padding: 0.75rem 0.5rem; font-weight: 600;">${order.symbol}</td>
                        <td style="padding: 0.75rem 0.5rem; color: ${color}; text-transform: uppercase;">${order.side}</td>
                        <td style="padding: 0.75rem 0.5rem;">${order.price || 'Market'}</td>
                        <td style="padding: 0.75rem 0.5rem;">${order.amount}</td>
                        <td style="padding: 0.75rem 0.5rem;">${order.status}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        } catch (e) {
            console.error("Error fetching history:", e);
        }
    }

    // Execute Trade (Updated for AI)
    async function executeTrade(signal, confidence) {
        // AI uses market orders for now
        const symbol = symbolSelect.value;
        const percentage = 10; // Default AI trade size

        log(`AI Executing ${signal.toUpperCase()} order for ${symbol}...`);

        try {
            const response = await fetch('/trading/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    side: signal.toLowerCase(),
                    type: 'market',
                    percentage: percentage
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                log(`SUCCESS: Order ${result.order_id} placed.`);
                fetchOrderHistory();
            } else {
                log(`FAILED: ${result.detail || 'Unknown error'}`);
            }
        } catch (e) {
            log(`System Error: ${e.message}`);
        }
    }

    // --- AI Logic ---

    async function runAnalysisAndTrade() {
        if (isAnalyzing) return;
        isAnalyzing = true;

        const symbol = symbolSelect.value;
        const geminiInput = document.getElementById('gemini_key');
        const isAuto = isAutoPilotActive;

        // Check if key is visible (meaning not saved) and empty
        if (geminiInput && geminiInput.offsetParent !== null && !geminiInput.value) {
            log("Error: Missing Gemini API Key");
            alert("Please enter Gemini API Key or Save it first.");
            isAnalyzing = false;
            if (isAuto) {
                stopAutoTrade();
            }
            return;
        }

        if (aiStatus) {
            aiStatus.textContent = "Scanning market...";
            aiStatus.style.background = "rgba(255, 255, 0, 0.2)";
        }

        try {
            // 1. Analyze
            const response = await fetch('/ai/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: symbol,
                    timeframe: '1h',
                    model: document.getElementById('ai-model').value,
                    risk_level: document.getElementById('risk-level').value,
                    strategy: document.getElementById('strategy').value,
                    active_agents: getActiveAgents()
                })
            });

            if (!response.ok) throw new Error("Analysis failed");
            const data = await response.json();

            // Update UI
            if (techContent) techContent.textContent = data.technical_analysis;
            if (fundContent) fundContent.textContent = data.fundamental_analysis;
            if (riskContent) riskContent.textContent = data.risk_assessment;
            if (signalText) {
                signalText.textContent = data.consensus_signal;
                signalText.className = `signal-${data.consensus_signal.toLowerCase()} signal-badge`;
            }
            if (confidenceText) confidenceText.textContent = `${(data.confidence_score * 100).toFixed(0)}% Conf.`;
            if (reasoningContent) reasoningContent.textContent = data.reasoning;
            if (aiOutput) aiOutput.style.display = 'grid';

            log(`Analysis Complete: ${data.consensus_signal} (${(data.confidence_score * 100).toFixed(0)}%)`);

            // 2. Auto-Trade Logic
            if (isAuto) {
                const confidenceThreshold = 0.8; // Only trade if > 80% confident

                if (data.confidence_score >= confidenceThreshold) {
                    if (data.consensus_signal === 'BUY' || data.consensus_signal === 'SELL') {
                        await executeTrade(data.consensus_signal, data.confidence_score);
                    } else {
                        log("Signal is HOLD. No action taken.");
                    }
                } else {
                    log(`Skipping trade: Confidence too low (< ${(confidenceThreshold * 100)}%)`);
                }
            }

            if (aiStatus) {
                aiStatus.textContent = isAuto ? "Auto-Pilot Active" : "Analysis Complete";
                aiStatus.style.background = "rgba(16, 185, 129, 0.2)";
            }

        } catch (error) {
            if (aiStatus) {
                aiStatus.textContent = "Error";
                aiStatus.style.background = "rgba(239, 68, 68, 0.2)";
            }
            log(`Error: ${error.message}`);
            console.error(error);
        } finally {
            isAnalyzing = false;
        }
    }

    const startAutoBtn = document.getElementById('start-auto-btn');
    const stopAutoBtn = document.getElementById('stop-auto-btn');
    let isAutoPilotActive = false;

    // ... (existing code) ...

    function startAutoTrade() {
        const intervalVal = document.getElementById('trading-interval').value;
        let ms = 3600000; // Default 1h
        if (intervalVal === '1m') ms = 60000;
        if (intervalVal === '5m') ms = 300000;
        if (intervalVal === '15m') ms = 900000;

        log(`Starting Auto-Pilot (Interval: ${intervalVal})...`);
        isAutoPilotActive = true;

        // Update UI
        if (startAutoBtn) startAutoBtn.disabled = true;
        if (stopAutoBtn) stopAutoBtn.disabled = false;
        if (aiStatus) {
            aiStatus.textContent = "Auto-Pilot Active";
            aiStatus.style.background = "rgba(16, 185, 129, 0.2)";
        }

        runAnalysisAndTrade(); // Run immediately
        autoTradeInterval = setInterval(runAnalysisAndTrade, ms);
    }

    function stopAutoTrade() {
        log("Stopping Auto-Pilot.");
        isAutoPilotActive = false;
        clearInterval(autoTradeInterval);
        autoTradeInterval = null;

        // Update UI
        if (startAutoBtn) startAutoBtn.disabled = false;
        if (stopAutoBtn) stopAutoBtn.disabled = true;
        if (aiStatus) {
            aiStatus.textContent = "System Idle";
            aiStatus.style.background = "transparent";
        }
    }

    if (startAutoBtn) {
        startAutoBtn.addEventListener('click', startAutoTrade);
    }

    if (stopAutoBtn) {
        stopAutoBtn.addEventListener('click', stopAutoTrade);
    }

    // --- Right Tab Logic ---
    window.switchRightTab = function (tab) {
        const logsPanel = document.getElementById('logs-panel');
        const chatPanel = document.getElementById('chat-panel');

        if (logsPanel) logsPanel.style.display = tab === 'logs' ? 'block' : 'none';
        if (chatPanel) chatPanel.style.display = tab === 'chat' ? 'flex' : 'none';

        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.textContent.includes('Logs') && tab === 'logs') btn.classList.add('active');
            else if (btn.textContent.includes('Assistant') && tab === 'chat') btn.classList.add('active');
            else if (btn.parentElement.classList.contains('tabs') && btn.parentElement.parentElement.id !== 'manual-panel') {
                // Only toggle active class for right tabs, not main mode tabs
                if (btn.textContent.includes('Logs') || btn.textContent.includes('Assistant')) btn.classList.remove('active');
            }
        });
    }

    window.sendDashboardMessage = async function () {
        const input = document.getElementById('dashboard-chat-input');
        const msg = input.value.trim();
        if (!msg) return;

        const history = document.getElementById('dashboard-chat-history');
        history.innerHTML += `<div class="chat-msg user" style="background: var(--accent-color); padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; align-self: flex-end; margin-left: 20%;">${msg}</div>`;
        input.value = '';

        const model = document.getElementById('chat-model-select') ? document.getElementById('chat-model-select').value : 'gemini-pro';

        try {
            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    context: 'market',
                    model: model
                })
            });
            const data = await response.json();
            history.innerHTML += `<div class="chat-msg ai" style="background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; align-self: flex-start; margin-right: 20%;">${data.response}</div>`;
            history.scrollTop = history.scrollHeight;
        } catch (e) {
            console.error(e);
        }
    }

    // Fetch Market Data
    async function fetchMarketData() {
        try {
            const res = await fetch('/trading/market-data');
            const tickers = await res.json();
            const tbody = document.getElementById('market-data-body');
            if (!tbody) return;

            tbody.innerHTML = '';

            if (tickers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="padding: 1rem; text-align: center; color: var(--text-secondary);">Loading market data...</td></tr>';
                return;
            }

            tickers.forEach(ticker => {
                const color = ticker.change >= 0 ? '#10b981' : '#ef4444';
                const sign = ticker.change >= 0 ? '+' : '';
                const row = `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 0.5rem;">${ticker.symbol}</td>
                        <td style="padding: 0.5rem;">${ticker.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td style="padding: 0.5rem; color: ${color};">${sign}${ticker.change.toFixed(2)}%</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        } catch (e) {
            console.error("Error fetching market data:", e);
        }
    }

    // Initial load
    fetchOrderHistory();
    fetchMarketData();
    setInterval(fetchMarketData, 10000); // Refresh every 10s
});
