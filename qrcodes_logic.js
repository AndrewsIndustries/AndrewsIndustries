const previewPane = document.getElementById('previewPane');
const previewFrame = document.getElementById('previewFrame');

function showPreview(url, e) {
    if (previewFrame.src !== url) previewFrame.src = url;
    previewPane.style.display = 'block';
    movePreview(e);
}

function movePreview(e) {
    let x = e.clientX + 20;
    let y = e.clientY + 20;
    
    // Keep preview inside window bounds
    if (x + 470 > window.innerWidth) x = e.clientX - 470;
    if (y + 320 > window.innerHeight) y = e.clientY - 320;

    previewPane.style.left = x + 'px';
    previewPane.style.top = y + 'px';
}

function hidePreview() {
    previewPane.style.display = 'none';
    previewFrame.src = 'about:blank'; // Stop loading/audio when hidden
}

async function triggerGenerator() {
    const repo = "AndrewsIndustries/AndrewsIndustries";
    const syncBtn = document.getElementById('syncBtn');
    
    let token = localStorage.getItem('andrews_gh_pat');
    if (!token) {
        token = prompt("Enter your GitHub Personal Access Token:");
        if (!token) return;
        localStorage.setItem('andrews_gh_pat', token);
    }

    syncBtn.innerText = "Triggering...";
    syncBtn.disabled = true;

    try {
        const response = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
            method: 'POST',
            headers: {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': `token ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event_type: 'generate-qrs'
            })
        });

        if (response.ok) {
            alert('Sync started! GitHub is now running the QR Generator. Refresh the page in 1-2 minutes to see changes.');
        } else {
            const err = await response.text();
            console.error(err);
            if (response.status === 401) {
                alert("GitHub Token invalid. Clearing token...");
                localStorage.removeItem('andrews_gh_pat');
            } else {
                alert("Failed to trigger sync. Check console for details.");
            }
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        syncBtn.innerText = "Sync QR Assets";
        syncBtn.disabled = false;
    }
}

async function loadData() {
    // Correcting the URL to ensure it pulls CSV data instead of HTML
    const BASE_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTp9TnMwxNNqwp3Ol3kjBaxvwvsyX9iLUltpNS6kMNhyARRYMYMIFwKNoW3D25XxACg2jk1MpKNOdCE/pub';
    const SHEET_CSV = `${BASE_URL}?output=csv`;
    
    const container = document.getElementById('qrContainer');
    const targetUrl = `${SHEET_CSV}&cache_buster=${Date.now()}`;

    try {
        let csvText;
        console.log("Fetching from:", targetUrl);

        // Attempt 1: Direct Fetch (Works when hosted on a server)
        try {
            const response = await fetch(targetUrl);
            if (response.ok) csvText = await response.text();
        } catch (e) {
            console.warn("Direct fetch blocked (CORS), trying proxy...");
        }

        // Attempt 2: AllOrigins Proxy Fallback (Works for local file://)
        if (!csvText) {
            const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(targetUrl)}`;
            const response = await fetch(proxyUrl);
            if (response.ok) csvText = await response.text();
        }

        if (!csvText) throw new Error("Could not access spreadsheet data. Ensure the sheet is 'Published to the web' as CSV.");
        
        const rows = csvText.split(/\r?\n/).filter(line => line.trim() !== "");
        container.innerHTML = ''; 

        if (rows.length <= 1) {
            container.innerHTML = `<div style="grid-column: span 5; text-align: center; opacity: 0.6;">No data found.</div>`;
            return;
        }

        rows.slice(1).forEach(row => { // skip header row
            const cols = row.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(c => c.replace(/"/g, '').trim());
            const link = cols[0];
            const name = cols[1];

            const safeFileName = name.trim().replace(/[^a-z0-9_]/gi, '_') + '.jpg';
            const localImgPath = `images/QRCodes/${safeFileName}`;

            if (name && link) {
                const item = document.createElement('div');
                item.className = 'qr-item';
                item.innerHTML = `
                    <div class="qr-name">${name}</div>
                    <a href="${link}" target="_blank">
                        <img src="${localImgPath}" 
                             onerror="this.src='https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(link)}'" 
                             alt="${name}" class="qr-image">
                    </a>
                    <a href="${link}" target="_blank" class="qr-link">Link</a>
                `;
                item.addEventListener('mouseenter', (e) => showPreview(link, e));
                item.addEventListener('mousemove', (e) => movePreview(e));
                item.addEventListener('mouseleave', hidePreview);
                container.appendChild(item);
            }
        });
    } catch (err) {
        container.innerHTML = `<div style="grid-column: span 5; color: #ef4444;">Failed to load spreadsheet data.</div>`;
        console.error(err);
    }
}

window.onload = loadData;
