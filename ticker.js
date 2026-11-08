document.addEventListener('DOMContentLoaded', () => {
    const ticker = document.getElementById('footer-ticker');
    const container = ticker ? ticker.parentElement : null;

    if (!ticker || !container) {
        console.error("[ticker] Ticker elements not found. Ensure an element with id='footer-ticker' exists inside its scrolling container.");
        return;
    }

    // The XML is published with this static site. Fetch it from the site's own
    // origin so GitHub Pages and custom-domain deployments do not depend on
    // cross-origin headers from raw.githubusercontent.com.
    const stockXmlUrl = new URL('data/Stock%20Watch.xml', document.baseURI);
    const pollIntervalMs = 10 * 60 * 1000;
    const maxBackoffMs = 30 * 60 * 1000;
    const baseBackoffMs = 30 * 1000;
    const requestTimeoutMs = 10 * 1000;
    const separator = ' \u00A0\u00A0\u00A0 | \u00A0\u00A0\u00A0 ';
    let consecutiveFailures = 0;
    let pollTimer;
    let position = container.clientWidth;
    let animationFrame;
    let lastKnownGoodText = ticker.textContent.trim();

    function getRetryDelay(response) {
        const retryAfter = response.headers.get('Retry-After');
        if (retryAfter) {
            const seconds = Number(retryAfter);
            if (Number.isFinite(seconds)) return Math.max(1000, seconds * 1000);
            const retryAt = Date.parse(retryAfter);
            if (Number.isFinite(retryAt)) return Math.max(1000, retryAt - Date.now());
        }

        const resetAt = Number(response.headers.get('X-RateLimit-Reset'));
        if (Number.isFinite(resetAt) && resetAt > 0) {
            return Math.max(1000, resetAt * 1000 - Date.now());
        }
        return null;
    }

    function logRateLimit(response) {
        const remainingHeader = response.headers.get('X-RateLimit-Remaining') ||
            response.headers.get('X-Ratelimit-Remaining');
        if (remainingHeader === null) return;

        const remaining = Number(remainingHeader);
        if (Number.isFinite(remaining)) {
            console.info(`[ticker] API rate-limit remaining: ${remaining}.`);
            if (remaining <= 0) console.warn('[ticker] Rate limit exhausted; retaining the current ticker and backing off.');
        }
    }

    function parseTickerEntries(xmlText) {
        const xmlDoc = new DOMParser().parseFromString(xmlText, 'application/xml');
        if (xmlDoc.getElementsByTagName('parsererror').length > 0 || !xmlDoc.documentElement) {
            throw new Error('Stock XML response was malformed');
        }

        const stocks = Array.from(xmlDoc.getElementsByTagName('Stock'));
        const entries = stocks.map(stock => {
            const symbol = stock.getAttribute('ticker')?.trim();
            if (!symbol) return null;

            const price = stock.getElementsByTagName('Price')[0]?.textContent?.trim() || 'N/A';
            const change = stock.getElementsByTagName('DaysChange')[0]?.textContent?.trim() || '0%';
            const status = stock.getElementsByTagName('warming_cooling')[0]?.textContent?.trim() || '';
            let display = `${symbol}: ${price} (${change})`;
            if (status && status.toLowerCase() !== 'nan') display += ` [${status}]`;
            return display;
        }).filter(Boolean);

        if (!entries.length) throw new Error('Stock XML contained no valid ticker entries');
        return entries;
    }

    async function refreshTicker() {
        const url = new URL(stockXmlUrl.href);
        url.searchParams.set('t', Date.now());
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

        try {
            console.info(`[ticker] Fetching stock XML from ${url.href}`);
            const response = await fetch(url.href, { cache: 'no-store', signal: controller.signal });
            logRateLimit(response);

            if (!response.ok) {
                const errorText = await response.text().catch(() => 'Unable to read error response body.');
                const retryDelay = getRetryDelay(response);
                const error = new Error(`Stock XML request failed: HTTP ${response.status} ${response.statusText}`);
                error.status = response.status;
                error.retryDelay = retryDelay;
                console.warn(`[ticker] ${error.message}. Response:`, errorText.slice(0, 500));
                throw error;
            }

            const xmlText = await response.text();
            if (!xmlText.trim()) throw new Error('Stock XML response was empty');
            const tickerEntries = parseTickerEntries(xmlText);

            // Commit a new display only after the entire response has been validated.
            const nextText = tickerEntries.join(separator);
            ticker.textContent = nextText;
            lastKnownGoodText = nextText;
            consecutiveFailures = 0;
            console.info(`[ticker] Updated ticker display with ${tickerEntries.length} stock entries (HTTP ${response.status}).`);
            return null;
        } catch (error) {
            consecutiveFailures += 1;
            if (lastKnownGoodText) ticker.textContent = lastKnownGoodText;
            const retryDelay = error.retryDelay || Math.min(maxBackoffMs, baseBackoffMs * (2 ** Math.min(consecutiveFailures - 1, 10)));

            if (error instanceof TypeError) {
                console.warn('[ticker] The browser could not access the stock feed. If the feed URL is changed to another origin, that server must allow this site with Access-Control-Allow-Origin. GitHub Pages is static and cannot host a server-side CORS proxy; use same-origin published XML or deploy a separately hosted proxy. The existing ticker display is being retained.');
            }
            console.error('[ticker] Refresh failed; preserving the last known ticker display.', {
                status: error.status || 'network/parse error',
                message: error.message,
                retryInMs: retryDelay,
                error
            });
            if (!lastKnownGoodText) ticker.textContent = 'Unable to load live stock data.';
            return retryDelay;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    async function poll() {
        let retryDelay;
        try {
            retryDelay = await refreshTicker();
        } catch (error) {
            // Defensive guard so an unexpected poll error never stops future refreshes.
            console.error('[ticker] Unexpected polling error; preserving the current display.', error);
            retryDelay = baseBackoffMs;
        }
        pollTimer = setTimeout(poll, retryDelay || pollIntervalMs);
    }

    function animate() {
        try {
            position -= 2;
            if (position < -ticker.offsetWidth) position = container.clientWidth;
            ticker.style.transform = `translateX(${position}px)`;
            animationFrame = requestAnimationFrame(animate);
        } catch (error) {
            console.error('[ticker] Animation failed; ticker data will continue to refresh.', error);
        }
    }

    window.addEventListener('pagehide', () => {
        clearTimeout(pollTimer);
        if (animationFrame) cancelAnimationFrame(animationFrame);
    }, { once: true });

    poll();
    animate();
});
