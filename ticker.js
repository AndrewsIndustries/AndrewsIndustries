document.addEventListener('DOMContentLoaded', async () => {
    const ticker = document.getElementById('footer-ticker');
    const container = ticker ? ticker.parentElement : null;

    if (!ticker || !container) {
        console.error("Ticker elements not found. Ensure you have an element with id='footer-ticker'.");
        return;
    }

    // Fetch live data from GitHub
    try {
        const response = await fetch('https://raw.githubusercontent.com/AndrewsIndustries/AndrewsIndustries/main/data/Stock%20Watch.xml?t=' + Date.now());
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "application/xml");
        
        // Target individual stock nodes for cleaner formatting
        const stocks = xmlDoc.querySelectorAll('Stock');
        const tickerData = Array.from(stocks).map(stock => {
            const symbol = stock.getAttribute('ticker') || 'N/A';
            const price = stock.querySelector('Price')?.textContent || '0.00';
            const change = stock.querySelector('ChangePercent')?.textContent || '0';
            const sign = parseFloat(change) >= 0 ? '+' : '';
            return `${symbol}: $${parseFloat(price).toFixed(2)} (${sign}${parseFloat(change).toFixed(2)}%)`;
        }).join(' \u00A0\u00A0\u00A0 | \u00A0\u00A0\u00A0 ');

        ticker.textContent = tickerData || "No stock data found.";
    } catch (error) {
        console.error("Error loading ticker data:", error);
        ticker.textContent = "Unable to load live stock data.";
    }

    let speed = 2; // Speed of the ticker (pixels per frame)
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