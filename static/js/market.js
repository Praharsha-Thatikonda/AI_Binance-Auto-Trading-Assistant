document.addEventListener('DOMContentLoaded', () => {
    // TradingView Widget
    new TradingView.widget({
        "width": "100%",
        "height": 500,
        "symbol": "BINANCE:BTCUSDT",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
    });

    // Chat Functionality
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn = document.querySelector('.send-btn');

    async function sendMessage() {
        const msg = chatInput.value.trim();
        if (!msg) return;

        // User Message
        chatHistory.innerHTML += `
            <div class="chat-msg user" style="background: var(--accent-color); padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; align-self: flex-end; margin-left: 20%; margin-bottom: 0.5rem;">
                ${msg}
            </div>
        `;
        chatInput.value = '';
        chatHistory.scrollTop = chatHistory.scrollHeight;

        // Get Model
        const model = document.getElementById('chat-model-select') ? document.getElementById('chat-model-select').value : 'gemini-pro';

        try {
            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: msg,
                    context: 'market_analysis_page',
                    model: model
                })
            });
            const data = await response.json();

            // AI Response
            chatHistory.innerHTML += `
                <div class="chat-msg ai" style="background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; align-self: flex-start; margin-right: 20%; margin-bottom: 0.5rem;">
                    ${data.response}
                </div>
            `;
            chatHistory.scrollTop = chatHistory.scrollHeight;

        } catch (e) {
            console.error(e);
            chatHistory.innerHTML += `
                <div class="chat-msg ai" style="background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 0.5rem; border-radius: 4px; font-size: 0.85rem; align-self: flex-start; margin-right: 20%; margin-bottom: 0.5rem;">
                    Error: Failed to get response.
                </div>
            `;
        }
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // Tab Switching
    window.switchAnalysis = function (tab) {
        // Update Buttons
        document.querySelectorAll('.analysis-tabs .tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent.toLowerCase().includes(tab) ||
                (tab === 'market' && btn.textContent.includes('Market')) ||
                (tab === 'geo' && btn.textContent.includes('Geopolitical')) ||
                (tab === 'business' && btn.textContent.includes('Business')) ||
                (tab === 'news' && btn.textContent.includes('News'))) {
                btn.classList.add('active');
            }
        });

        // Update Panels
        document.querySelectorAll('.analysis-content .panel').forEach(panel => {
            panel.style.display = 'none';
        });

        const panelId = tab === 'market' ? 'market-panel' :
            tab === 'geo' ? 'geo-panel' :
                tab === 'business' ? 'business-panel' : 'news-panel';

        const target = document.getElementById(panelId);
        if (target) target.style.display = 'block';
    }
});
