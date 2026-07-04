/**
 * Core Application Logic
 * Handles global state, time synchronization, and caching.
 */

const AppCore = {
    state: {
        serverTimeOffset: 0,
        lastFetch: {},
        config: {}
    },

    init: function () {
        this.startClock();
        this.restoreState();
        console.log("App Core Initialized");
    },

    // --- Time & Date ---
    startClock: function () {
        const clockEl = document.getElementById('app-clock');
        const dateEl = document.getElementById('app-date');

        if (!clockEl && !dateEl) return;

        const update = () => {
            const now = new Date();

            // Format Time: HH:MM:SS.ms
            const timeStr = now.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            const ms = String(now.getMilliseconds()).padStart(3, '0');

            // Format Date: YYYY-MM-DD
            const dateStr = now.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });

            if (clockEl) clockEl.innerHTML = `${timeStr}<span style="font-size:0.7em; opacity:0.7">.${ms}</span>`;
            if (dateEl) dateEl.textContent = dateStr;

            // Dispatch global time event for other components
            window.dispatchEvent(new CustomEvent('app-tick', { detail: { time: now } }));
        };

        setInterval(update, 50); // Update every 50ms for smooth ms display
        update();
    },

    // --- Caching & Data Fetching ---
    /**
     * Fetch data with built-in caching (localStorage)
     * @param {string} url - API Endpoint
     * @param {object} options - Fetch options
     * @param {number} cacheDuration - Cache duration in seconds (0 to disable)
     */
    fetchWithCache: async function (url, options = {}, cacheDuration = 0) {
        const cacheKey = `cache_${url}`;

        // 1. Check Cache
        if (cacheDuration > 0 && options.method === 'GET') {
            const cached = localStorage.getItem(cacheKey);
            if (cached) {
                const { data, timestamp } = JSON.parse(cached);
                const age = (Date.now() - timestamp) / 1000;
                if (age < cacheDuration) {
                    console.log(`[Cache] Hit for ${url}`);
                    return { ok: true, json: () => Promise.resolve(data), fromCache: true };
                }
            }
        }

        // 2. Network Request
        try {
            const res = await fetch(url, options);
            if (res.ok && cacheDuration > 0 && options.method === 'GET') {
                const data = await res.clone().json();
                localStorage.setItem(cacheKey, JSON.stringify({
                    data: data,
                    timestamp: Date.now()
                }));
            }
            return res;
        } catch (e) {
            console.error(`[Fetch] Error fetching ${url}`, e);
            // Fallback to stale cache if available
            const cached = localStorage.getItem(cacheKey);
            if (cached) {
                console.warn(`[Cache] Using stale data for ${url}`);
                const { data } = JSON.parse(cached);
                return { ok: true, json: () => Promise.resolve(data), fromCache: true, stale: true };
            }
            throw e;
        }
    },

    // --- State Management ---
    saveState: function (key, value) {
        localStorage.setItem(`app_state_${key}`, JSON.stringify(value));
        this.state[key] = value;
    },

    restoreState: function () {
        // Restore relevant state if needed
    },

    clearCache: function () {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('cache_')) localStorage.removeItem(key);
        });
        console.log("Cache cleared");
    }
};

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    AppCore.init();
});
