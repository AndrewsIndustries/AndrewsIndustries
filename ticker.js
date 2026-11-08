document.addEventListener('DOMContentLoaded', async () => {
    const ticker = document.getElementById('footer-ticker');
    const container = ticker ? ticker.parentElement : null;

    if (!ticker || !container) {
        console.error("Ticker elements not found. Ensure you have an element with id='footer-ticker'.");
        return;
    }

    const stockXmlUrl = new URL(
        'data/Stock%20Watch.xml',
        'https://raw.githubusercontent.com/AndrewsIndustries/AndrewsIndustries/main/'
    );
    stockXmlUrl.searchParams.set('t', Date.now());

    // Keep the currently displayed ticker when a request returns bad or empty data.
    const previousTickerText = ticker.textContent.trim();

    try {
        console.log(`[ticker] Fetching stock XML from ${stockXmlUrl.href}`);
        const response = await fetch(stockXmlUrl.href, { cache: 'no-store' });

        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unable to read error response body.');
            console.warn(`[ticker] Stock XML request failed: HTTP ${response.status} ${response.statusText}. Response:`, errorText.slice(0, 500));
            throw new Error(`Stock XML request failed with HTTP ${response.status}`);
        }

        const xmlText = await response.text();
        console.log(`[ticker] Received ${xmlText.length} characters of stock XML (HTTP ${response.status}).`);
        if (!xmlText.trim()) {
            console.warn('[ticker] Stock XML response was empty; keeping the previous ticker display.');
            throw new Error('Stock XML response was empty');
        }

        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, 'application/xml');
        const parseErrors = xmlDoc.getElementsByTagName('parsererror');
        if (parseErrors.length > 0 || !xmlDoc.documentElement) {
            console.warn('[ticker] Stock XML could not be parsed. Raw response preview:', xmlText.slice(0, 500));
            throw new Error('Stock XML response was malformed');
        }

        const stocks = Array.from(xmlDoc.getElementsByTagName('Stock'));
        if (stocks.length === 0) {
            console.warn('[ticker] Stock XML contained no <Stock> entries; keeping the previous ticker display.');
            throw new Error('Stock XML contained no stock entries');
        }

        const tickerEntries = stocks.map(stock => {
            const symbol = stock.getAttribute('ticker')?.trim();
            if (!symbol) return null;

            const price = stock.getElementsByTagName('Price')[0]?.textContent?.trim() || 'N/A';
            const change = stock.getElementsByTagName('DaysChange')[0]?.textContent?.trim() || '0%';
            const status = stock.getElementsByTagName('warming_cooling')[0]?.textContent?.trim() || '';

            let display = `${symbol}: ${price} (${change})`;
            if (status && status.toLowerCase() !== 'nan') {
                display += ` [${status}]`;
            }
            return display;
        }).filter(Boolean);

        if (tickerEntries.length === 0) {
            console.warn('[ticker] Stock XML contained no valid ticker entries; keeping the previous ticker display.');
            throw new Error('Stock XML contained no valid ticker entries');
        }

        ticker.textContent = tickerEntries.join(' \u00A0\u00A0\u00A0 | \u00A0\u00A0\u00A0 ');
        console.log(`[ticker] Updated ticker display with ${tickerEntries.length} stock entries.`);
    } catch (error) {
        console.error('[ticker] Unable to refresh live stock data; preserving the last display when available:', error);
        if (!previousTickerText) {
            ticker.textContent = 'Unable to load live stock data.';
        }
    }

    const speed = 2; // Speed of the ticker (pixels per frame)
    let position = container.clientWidth;

    function animate() {
        position -= speed;

        if (position < -ticker.offsetWidth) {
            position = container.clientWidth;
        }

        ticker.style.transform = `translateX(${position}px)`;
        requestAnimationFrame(animate);
    }

    animate();
});
