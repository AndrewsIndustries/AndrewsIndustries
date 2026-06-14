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
        
        // Using getElementsByTagName for broader XML compatibility
        const stocks = xmlDoc.getElementsByTagName('Stock');
        const tickerData = Array.from(stocks).map(stock => {
            const symbol = stock.getAttribute('ticker') || 'N/A';
            const price = stock.getElementsByTagName('Price')[0]?.textContent || 'N/A';
            const change = stock.getElementsByTagName('DaysChange')[0]?.textContent || '0%';
            const status = stock.getElementsByTagName('warming_cooling')[0]?.textContent || '';
            
            // Use the pre-formatted strings from the Python sync script
            let display = `${symbol}: ${price} (${change})`;
            if (status && status.toLowerCase() !== 'nan' && status.trim() !== '') {
                display += ` [${status}]`;
            }
            return display;
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