let activeTab = 'spot';
let userAssets = {}; // Stores { symbol: { balance: 0, price: 0, web3_balance: 0 } }
let allTransactions = []; // Stores all fetched transactions
let web3Wallets = []; // Stores fetched web3 wallets
let tradingMode = 'manual'; // manual or auto

document.addEventListener('DOMContentLoaded', () => {
    fetchAssets();
    fetchTransactions();
    fetchTradingMode(); // Fetch initial state

    // Amount Input Listener for USD Preview
    const amountInput = document.getElementById('modalAmount');
    if (amountInput) {
        amountInput.addEventListener('input', updateUsdPreview);
    }

    // Filter Listeners
    const filters = ['filterType', 'filterStatus', 'filterSearch'];
    filters.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', filterTransactions);
            el.addEventListener('change', filterTransactions);
        }
    });
});

// --- Modal Logic ---

function openModal(action) {
    const modal = document.getElementById('actionModal');
    const title = document.getElementById('modalTitle');
    const fields = ['networkField', 'addressField', 'amountField', 'qrCodeField', 'sourceWalletField', 'memoField'];

    // Reset Fields
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) el.style.display = 'none';
    });
    document.getElementById('modalAmount').value = '';
    document.getElementById('modalAddress').value = '';
    document.getElementById('modalMemo').value = '';
    document.getElementById('usdPreview').innerText = '≈ $0.00';

    // Set Title & Fields
    let actionTitle = action.charAt(0).toUpperCase() + action.slice(1);
    title.innerText = actionTitle;

    if (action === 'deposit') {
        // Deposit: To Wallet (Spot/Web3) -> Show QR
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "To Wallet";
        document.getElementById('networkField').style.display = 'block';
        document.getElementById('qrCodeField').style.display = 'block';
        generateQRCode();
    } else if (action === 'withdraw') {
        // Withdraw: From Wallet -> To Address
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "From Wallet";
        document.getElementById('networkField').style.display = 'block';
        document.getElementById('addressField').style.display = 'block';
        document.getElementById('amountField').style.display = 'block';
        document.getElementById('memoField').style.display = 'block';
    } else if (action === 'transfer') {
        // Transfer: Internal
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "From Wallet";
        document.getElementById('addressField').style.display = 'block';
        document.querySelector('#addressField label').innerText = "Recipient Username/Email";
        document.getElementById('amountField').style.display = 'block';
    } else if (action === 'send') {
        // Send: From Wallet -> To Address
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "From Wallet";
        document.getElementById('addressField').style.display = 'block';
        document.getElementById('amountField').style.display = 'block';
    } else if (action === 'receive') {
        // Receive: To Wallet -> Show QR
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "To Wallet";
        document.getElementById('qrCodeField').style.display = 'block';
        generateQRCode();
    } else if (action === 'exchange' || action === 'convert') {
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "From Wallet";
        document.getElementById('amountField').style.display = 'block';
    } else if (action === 'web3_send') {
        title.innerText = "Send Crypto (Web3)";
        document.getElementById('sourceWalletField').style.display = 'block';
        document.querySelector('#sourceWalletField label').innerText = "From Wallet";
        document.getElementById('addressField').style.display = 'block';
        document.getElementById('amountField').style.display = 'block';
        selectModalWallet('web3');
    }

    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('actionModal').style.display = 'none';
}

function selectModalWallet(type) {
    document.querySelectorAll('.wallet-select-btn').forEach(btn => {
        if (btn.dataset.value === type) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    document.getElementById('modalWalletType').value = type;

    // If deposit/receive, regenerate QR for selected wallet type
    const action = document.getElementById('modalTitle').innerText.toLowerCase();
    if (action.includes('deposit') || action.includes('receive')) {
        generateQRCode();
    }
}

function updateNetworkOptions() {
    // Logic to update networks based on selected coin
    // For now, static
}

function generateQRCode() {
    const currency = document.getElementById('modalCurrency').value;
    const walletType = document.getElementById('modalWalletType').value;

    let address = "Loading...";

    if (walletType === 'web3' && web3Wallets.length > 0) {
        // Use first web3 wallet address
        address = web3Wallets[0].address;
    } else {
        // Mock spot address
        address = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F";
    }

    document.getElementById('depositAddress').innerText = address;
    const qrContainer = document.getElementById('qrcode');
    qrContainer.innerHTML = '';
    new QRCode(qrContainer, {
        text: address,
        width: 128,
        height: 128
    });
}

function copyDepositAddress() {
    const addr = document.getElementById('depositAddress').innerText;
    navigator.clipboard.writeText(addr).then(() => showToast('Address copied!'));
}

async function submitAction() {
    const action = document.getElementById('modalTitle').innerText.split(' ')[0].toLowerCase();
    const amount = parseFloat(document.getElementById('modalAmount').value);
    const address = document.getElementById('modalAddress').value;
    const currency = document.getElementById('modalCurrency').value;
    const wallet = document.getElementById('modalWalletType').value;
    const memo = document.getElementById('modalMemo').value;

    if (isNaN(amount) && action !== 'deposit' && action !== 'receive') {
        showToast('Invalid amount', 'error');
        return;
    }

    const btn = document.getElementById('modalSubmitBtn');
    btn.disabled = true;
    btn.innerText = "Processing...";

    try {
        let url = '/api/wallet/transaction';
        let payload = {};

        if (action === 'convert') {
            // Simulation for convert
            setTimeout(() => {
                showToast('Conversion simulated (UI limitation)', 'success');
                closeModal();
                btn.disabled = false;
                btn.innerText = "Confirm";
            }, 1000);
            return;
        } else if (action === 'send' && wallet === 'web3') {
            // Web3 Send
            url = '/api/wallet/web3/send';
            payload = {
                to_address: address,
                amount: amount,
                currency: currency
            };
        } else {
            // Standard Transaction
            payload = {
                type: action,
                currency: currency,
                amount: amount,
                to_address: address,
                wallet_type: wallet,
                memo: memo // Pass memo if backend supports it (it doesn't yet, but good for future)
            };

            if (action === 'send') payload.type = 'withdraw';
            if (action === 'receive') {
                payload.type = 'deposit';
            }
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            showToast(`${action} Successful!`, 'success');
            closeModal();
            fetchAssets();
            fetchTransactions();
        } else {
            showToast(`Error: ${data.detail}`, 'error');
        }

    } catch (e) {
        console.error(e);
        showToast('Request failed', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "Confirm";
        }
    }
}

// --- Data Fetching ---

async function fetchAssets() {
    try {
        const response = await fetch('/api/wallet/assets');
        const data = await response.json();

        // Update Total Balance
        const totalBalEl = document.getElementById('total-balance');
        if (totalBalEl) totalBalEl.innerText = `$${data.total_balance_usdt}`;

        // Update Binance Balance
        const binanceBalEl = document.getElementById('binance-balance');
        if (binanceBalEl) {
            if (data.exchange_balance_usdt > 0) {
                binanceBalEl.innerText = `$${data.exchange_balance_usdt}`;
            } else {
                binanceBalEl.innerText = "Not Connected";
                binanceBalEl.style.fontSize = "1.2rem";
                binanceBalEl.style.color = "var(--text-secondary)";
            }
        }

        // Update Web3 Balance Display
        const web3BalEl = document.getElementById('web3-balance-display');
        if (web3BalEl) {
            let web3Total = 0;
            if (data.web3_assets) {
                data.web3_assets.forEach(a => web3Total += (a.value_usdt || 0));
            }
            web3BalEl.innerText = `$${web3Total.toFixed(2)}`;
        }

        // Populate Assets Table
        const tbody = document.querySelector('.assets-table tbody');
        if (tbody) {
            tbody.innerHTML = '';
            if (data.assets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 1rem; color: var(--text-secondary);">No assets found.</td></tr>';
            } else {
                data.assets.forEach(asset => {
                    // Update Global State
                    if (!userAssets[asset.symbol]) userAssets[asset.symbol] = { balance: 0, price: 0, web3_balance: 0 };
                    userAssets[asset.symbol].balance = asset.amount;
                    userAssets[asset.symbol].price = asset.current_price || 0;

                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                    tr.innerHTML = `
                        <td style="padding: 0.5rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div style="width: 24px; height: 24px; background: rgba(255,255,255,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem;">${asset.symbol[0]}</div>
                                <span>${asset.symbol}</span>
                            </div>
                        </td>
                        <td style="padding: 0.5rem; font-family: 'JetBrains Mono';">${asset.amount}</td>
                        <td style="padding: 0.5rem; font-family: 'JetBrains Mono';">$${asset.value_usdt}</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

        // Check Web3 Wallet Existence
        checkWeb3Wallet();

    } catch (error) {
        console.error('Error fetching assets:', error);
        showToast('Failed to load assets', 'error');
    }
}

async function fetchTransactions() {
    try {
        const response = await fetch('/api/wallet/transactions');
        if (response.ok) {
            allTransactions = await response.json();
            filterTransactions();
        }
    } catch (e) {
        console.error("Error fetching transactions:", e);
    }
}

function filterTransactions() {
    const typeFilter = document.getElementById('filterType')?.value || 'all';
    const statusFilter = document.getElementById('filterStatus')?.value || 'all';
    const searchFilter = document.getElementById('filterSearch')?.value.toLowerCase() || '';

    const filtered = allTransactions.filter(tx => {
        const matchesType = typeFilter === 'all' || tx.type.toLowerCase() === typeFilter;
        const matchesStatus = statusFilter === 'all' || (tx.status && tx.status.toLowerCase() === statusFilter);
        const matchesSearch = !searchFilter ||
            tx.type.toLowerCase().includes(searchFilter) ||
            tx.asset.toLowerCase().includes(searchFilter) ||
            (tx.amount && tx.amount.toString().includes(searchFilter));

        return matchesType && matchesStatus && matchesSearch;
    });

    renderTransactions(filtered);
}

function renderTransactions(transactions) {
    const list = document.querySelector('.tx-list');
    if (!list) return;

    list.innerHTML = '';

    if (transactions.length === 0) {
        list.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">No transactions found.</div>';
        return;
    }

    transactions.forEach(tx => {
        let icon = '🔄';
        let color = '#3b82f6';
        let sign = '';
        let amountClass = '';

        const type = tx.type.toLowerCase();
        if (type === 'deposit') { icon = '⬇️'; color = '#10b981'; sign = '+'; amountClass = 'text-green-400'; }
        else if (type === 'withdraw') { icon = '📤'; color = '#ef4444'; sign = '-'; amountClass = 'text-red-400'; }
        else if (type === 'buy') { icon = '🛒'; color = '#ef4444'; sign = ''; }
        else if (type === 'sell') { icon = '💰'; color = '#10b981'; sign = ''; }
        else if (type === 'web3_send') { icon = '🦊'; color = '#8b5cf6'; sign = '-'; }

        const item = document.createElement('div');
        item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05);';

        let subtext = tx.timestamp || tx.datetime;
        if (tx.tx_hash) subtext += ` <span style="font-family:'JetBrains Mono'; font-size:0.75rem; opacity:0.7;">${tx.tx_hash.substring(0, 6)}...</span>`;

        // Status Badge
        let statusColor = '#9ca3af';
        if (tx.status === 'COMPLETED') statusColor = '#10b981';
        if (tx.status === 'FAILED') statusColor = '#ef4444';
        if (tx.status === 'PENDING') statusColor = '#f59e0b';

        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="font-size: 1.2rem; color: ${color};">${icon}</div>
                <div>
                    <div style="font-weight: 500;">${tx.type} ${tx.asset}</div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">${subtext}</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-family: 'JetBrains Mono'; ${type === 'deposit' ? 'color: #10b981;' : (type === 'withdraw' ? 'color: #ef4444;' : '')}">
                    ${sign}${tx.amount} ${tx.asset}
                </div>
                <div style="font-size: 0.7rem; color: ${statusColor}; border: 1px solid ${statusColor}; border-radius: 4px; padding: 1px 4px; display: inline-block; margin-top: 2px;">
                    ${tx.status}
                </div>
            </div>
        `;
        list.appendChild(item);
    });
}

// --- Web3 Logic ---

async function checkWeb3Wallet() {
    try {
        const response = await fetch('/api/wallet/web3/info');
        if (response.ok) {
            const data = await response.json();
            web3Wallets = data.wallets || [];

            const intro = document.getElementById('web3-intro');
            const dashboard = document.getElementById('web3-dashboard');

            if (web3Wallets.length > 0) {
                if (intro) intro.style.display = 'none';
                if (dashboard) dashboard.style.display = 'flex';
                renderWalletList();
            } else {
                if (intro) intro.style.display = 'block';
                if (dashboard) dashboard.style.display = 'none';
            }
        }
    } catch (e) {
        console.log("No Web3 wallet found or error", e);
    }
}

function renderWalletList() {
    const list = document.getElementById('web3-wallet-list');
    if (!list) return;
    list.innerHTML = '';

    web3Wallets.forEach((w, index) => {
        const div = document.createElement('div');
        div.className = 'wallet-list-item';
        div.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:bold;">Wallet ${index + 1}</span>
                <span style="font-size:0.75rem; color:var(--text-secondary);">${w.chain}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.25rem;">
                <div style="display:flex; flex-direction:column;">
                    <span style="font-size:0.65rem; color:var(--text-secondary);">Public Key</span>
                    <span style="font-family:'JetBrains Mono'; font-size:0.8rem; opacity:0.8;">${w.address.substring(0, 6)}...${w.address.substring(38)}</span>
                </div>
                <div style="display:flex; gap:0.5rem;">
                    <span style="font-size:0.75rem; color:#10b981;">${w.balance ? w.balance.toFixed(4) : '0.0000'} ETH</span>
                </div>
            </div>
            <div style="display:flex; gap:0.5rem; margin-top:0.5rem; justify-content:flex-end;">
                <button class="btn-secondary btn-sm" style="padding:2px 6px; font-size:0.7rem;" onclick="showWalletQR('${w.address}')">QR</button>
                <button class="btn-secondary btn-sm" style="padding:2px 6px; font-size:0.7rem;" onclick="togglePrivateKey(this, '${w.private_key}')">Key</button>
                <button class="btn-secondary btn-sm" style="padding:2px 6px; font-size:0.7rem; color:#ef4444; border-color:rgba(239,68,68,0.3);" onclick="deleteWeb3Wallet('${w.address}')">🗑️</button>
            </div>
        `;
        list.appendChild(div);
    });
}

async function deleteWeb3Wallet(address) {
    if (!confirm("Are you sure you want to delete this wallet? This action cannot be undone.")) return;

    try {
        const response = await fetch('/api/wallet/web3/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address: address })
        });

        if (response.ok) {
            showToast("Wallet deleted successfully", "success");
            checkWeb3Wallet();
        } else {
            const data = await response.json();
            showToast("Error: " + data.detail, "error");
        }
    } catch (e) {
        showToast("Request failed", "error");
    }
}

function showWalletQR(address) {
    const modal = document.getElementById('qrModal');
    const qrContainer = document.getElementById('walletQrCode');
    const addrText = document.getElementById('walletQrAddress');

    qrContainer.innerHTML = '';
    new QRCode(qrContainer, {
        text: address,
        width: 150,
        height: 150
    });

    addrText.innerText = address;
    modal.style.display = 'flex';
}

function togglePrivateKey(btn, key) {
    if (btn.innerText === 'Key') {
        navigator.clipboard.writeText(key).then(() => showToast('Private Key copied!'));
        btn.innerText = 'Copied';
        setTimeout(() => btn.innerText = 'Key', 2000);
    }
}

async function createWeb3Wallet() {
    const btn = document.querySelector('.web3-btn');
    if (btn) {
        btn.innerText = "Creating...";
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/wallet/web3/create', { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            showToast("Web3 Wallet Created!", 'success');
            checkWeb3Wallet();
        } else {
            showToast("Error: " + data.detail, 'error');
        }
    } catch (e) {
        showToast("Request failed", 'error');
    } finally {
        if (btn) {
            btn.innerText = "Create Wallet";
            btn.disabled = false;
        }
    }
}

// --- Chat Logic ---

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    // Add User Message
    addMessage(msg, 'user');
    input.value = '';

    // Show typing indicator
    const typingId = 'typing-' + Date.now();
    addMessage('Thinking...', 'bot', typingId);

    try {
        const response = await fetch('/api/wallet/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });

        const data = await response.json();

        // Remove typing indicator
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();

        addMessage(data.response, 'bot');

    } catch (e) {
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        addMessage("Sorry, I can't connect right now.", 'bot');
    }
}

function addMessage(text, sender, id = null) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-msg ${sender}`;
    div.innerText = text;
    if (id) div.id = id;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// --- Trading Mode Logic ---

async function fetchTradingMode() {
    try {
        const response = await fetch('/api/wallet/trading_mode');
        if (response.ok) {
            const data = await response.json();
            tradingMode = data.mode;
            updateTradingModeUI();
        }
    } catch (e) {
        console.error("Error fetching trading mode:", e);
    }
}

async function toggleTradingMode() {
    const newMode = tradingMode === 'manual' ? 'auto' : 'manual';

    try {
        const response = await fetch('/api/wallet/trading_mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: newMode })
        });

        if (response.ok) {
            tradingMode = newMode;
            updateTradingModeUI();
            showToast(`Switched to ${newMode === 'auto' ? 'Auto-Pilot' : 'Manual'} Mode`);
        }
    } catch (e) {
        showToast("Failed to switch mode", "error");
    }
}

function updateTradingModeUI() {
    const toggle = document.getElementById('tradingModeToggle');
    const icon = document.getElementById('tradingModeIcon');
    const text = document.getElementById('tradingModeText');

    if (tradingMode === 'auto') {
        toggle.classList.add('active');
        icon.innerText = '🤖';
        text.innerText = 'Auto-Pilot: ON';
    } else {
        toggle.classList.remove('active');
        icon.innerText = '👤';
        text.innerText = 'Auto-Pilot: OFF';
    }
}

// --- Helpers ---

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) {
        // Create container if not exists
        const c = document.createElement('div');
        c.id = 'toast-container';
        c.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(c);
    }

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: ${type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(16, 185, 129, 0.9)'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        backdrop-filter: blur(5px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-size: 0.9rem;
        animation: slideIn 0.3s ease-out forwards;
        display: flex;
        align-items: center;
        gap: 8px;
    `;
    toast.innerHTML = `<span>${type === 'error' ? '⚠️' : '✅'}</span> ${message}`;

    document.getElementById('toast-container').appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setMaxAmount() {
    const currency = document.getElementById('modalCurrency').value;
    const walletType = document.getElementById('modalWalletType').value;

    if (!userAssets[currency]) return;

    let max = 0;
    if (walletType === 'web3') {
        max = userAssets[currency].web3_balance || 0;
    } else {
        max = userAssets[currency].balance || 0;
    }

    document.getElementById('modalAmount').value = max;
    updateUsdPreview();
}

function updateUsdPreview() {
    const amount = parseFloat(document.getElementById('modalAmount').value) || 0;
    const currency = document.getElementById('modalCurrency').value;
    const price = userAssets[currency]?.price || 0;

    const val = amount * price;
    const previewEl = document.getElementById('usdPreview');
    if (previewEl) {
        previewEl.innerText = `≈ $${val.toFixed(2)}`;
    }
}

function exportKeys() {
    // Demo function
    showToast('Exporting keys to secure file...', 'info');
}
