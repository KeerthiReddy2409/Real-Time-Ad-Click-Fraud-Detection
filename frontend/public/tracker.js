(function() {
    const API_URL = 'http://localhost:8000/api/v1/verify';
    let mouseEvents = [];
    let isTracking = false;
    
    // Generate a session ID
    const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36);
    
    // Simple device fingerprint (will be enhanced later)
    const deviceFingerprint = navigator.userAgent + '|' + screen.width + 'x' + screen.height;
    
    // Track mouse movements
    document.addEventListener('mousemove', (e) => {
        if (!isTracking) return;
        mouseEvents.push({
            x: e.clientX,
            y: e.clientY,
            timestamp: performance.now()
        });
        // Keep only last 200 events to avoid huge payloads
        if (mouseEvents.length > 200) mouseEvents.shift();
    });
    
    // Start tracking on page load or when needed
    function startTracking() {
        isTracking = true;
        mouseEvents = [];
        console.log('Tracking started');
    }
    
    function stopTrackingAndSend() {
        isTracking = false;
        const payload = {
            session_id: sessionId,
            device_fingerprint: deviceFingerprint,
            user_agent: navigator.userAgent,
            mouse_events: mouseEvents,
            click_timestamp: performance.now(),
            page_url: window.location.href
        };
        
        fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('log').innerHTML = `
                <strong>Verdict:</strong> ${data.verdict}<br>
                <strong>Confidence:</strong> ${data.confidence}<br>
                <strong>Reason:</strong> ${data.reason}
            `;
        })
        .catch(err => {
            document.getElementById('log').innerHTML = `Error: ${err.message}`;
        });
        
        mouseEvents = [];
    }
    
    document.getElementById('testBtn').addEventListener('click', () => {
        stopTrackingAndSend();
        startTracking(); // restart tracking for next click
    });
    
    // Start tracking immediately
    startTracking();
})();