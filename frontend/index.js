// API Endpoint configuration
const API_BASE_URL = "http://localhost:8000";

// Accra sites database coordinates
const RISK_ZONES = {
    "korle lagoon": { lat: 5.5344, lon: -0.2197, name: "Korle Lagoon / Odaw Mouth", color: "#ff4b5c", zoom: 14 },
    "odaw river": { lat: 5.5500, lon: -0.2167, name: "Odaw River Basin", color: "#ff8e53", zoom: 14 },
    "sakumono ramsar site": { lat: 5.6294, lon: -0.0431, name: "Sakumono Ramsar Site", color: "#9a4eff", zoom: 13 },
    "densu delta ramsar site": { lat: 5.5167, lon: -0.3333, name: "Densu Delta Ramsar Site", color: "#00f2fe", zoom: 13 }
};

let map;
let zoneCircles = {};
let activeAlerts = [];
let lastScanResult = null;
let currentActiveView = "rgb"; // rgb, ndvi, mndwi

// Initial Setup
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initComparisonSlider();
    fetchAlerts();
    updateLiveAnalytics();
    setupChat();
    setupTabs();
});

// 1. Initialize Map
function initMap() {
    // Center map around Accra Central
    map = L.map("map", {
        zoomControl: true,
        attributionControl: false
    }).setView([5.56, -0.19], 12);

    // Dark Map Tiles (CartoDB Dark Matter)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19
    }).addTo(map);

    // Draw high-risk ecological buffers
    for (const [key, zone] of Object.entries(RISK_ZONES)) {
        const circle = L.circle([zone.lat, zone.lon], {
            color: zone.color,
            fillColor: zone.color,
            fillOpacity: 0.15,
            radius: 800 // 800 meter buffer radius
        }).addTo(map);

        circle.bindPopup(`
            <div class="map-popup">
                <h4>${zone.name}</h4>
                <p>Coordinates: ${zone.lat}, ${zone.lon}</p>
                <button class="popup-scan-btn" onclick="triggerDirectScan('${key}')">Scan and Detect</button>
            </div>
        `);
        
        zoneCircles[key] = circle;
    }
}

// 2. Initialize Split Comparison Slider
function initComparisonSlider() {
    const slider = document.getElementById("comparison-slider");
    const handle = document.getElementById("slider-handle");
    const baseline = document.querySelector(".baseline-container");

    let isDragging = false;

    const setSliderPosition = (xPos) => {
        const rect = slider.getBoundingClientRect();
        let percentage = ((xPos - rect.left) / rect.width) * 100;
        
        // Bounds checking
        if (percentage < 0) percentage = 0;
        if (percentage > 100) percentage = 100;

        // Apply clip path and handle position
        baseline.style.clipPath = `polygon(0 0, ${percentage}% 0, ${percentage}% 100%, 0 100%)`;
        handle.style.left = `${percentage}%`;
    };

    // Mouse movements
    handle.addEventListener("mousedown", () => isDragging = true);
    window.addEventListener("mouseup", () => isDragging = false);
    
    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        setSliderPosition(e.clientX);
    });

    // Touch movements for mobile
    handle.addEventListener("touchstart", () => isDragging = true);
    window.addEventListener("touchend", () => isDragging = false);
    window.addEventListener("touchmove", (e) => {
        if (!isDragging) return;
        setSliderPosition(e.touches[0].clientX);
    });

    // Set initial position at 50%
    baseline.style.clipPath = `polygon(0 0, 50% 0, 50% 100%, 0 100%)`;
    handle.style.left = `50%`;
}

// 3. Tab Toggles (RGB, NDVI, MNDWI)
function setupTabs() {
    const tabs = document.querySelectorAll(".tab-btn");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            
            currentActiveView = tab.getAttribute("data-view");
            updateComparisonImages();
        });
    });
}

function updateComparisonImages() {
    if (!lastScanResult) return;
    
    const baselineImg = document.getElementById("baseline-img");
    const currentImg = document.getElementById("current-img");
    
    const baseKey = `baseline_${currentActiveView}`;
    const currKey = `current_${currentActiveView}`;
    
    if (lastScanResult[baseKey] && lastScanResult[currKey]) {
        let baseSrc = lastScanResult[baseKey];
        let currSrc = lastScanResult[currKey];
        
        // Only prepend base URL if it's a relative static path
        if (!baseSrc.startsWith("http://") && !baseSrc.startsWith("https://")) {
            baseSrc = API_BASE_URL + baseSrc;
        }
        if (!currSrc.startsWith("http://") && !currSrc.startsWith("https://")) {
            currSrc = API_BASE_URL + currSrc;
        }
        
        baselineImg.src = baseSrc;
        currentImg.src = currSrc;
    }
}

// 4. Fetch Active Alerts List
async function fetchAlerts() {
    const listContainer = document.getElementById("alert-list");
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/alerts`);
        const data = await response.json();
        
        listContainer.innerHTML = "";
        
        if (data.status === "success" && data.alerts.length > 0) {
            activeAlerts = data.alerts;
            
            data.alerts.forEach((alert, idx) => {
                const card = document.createElement("div");
                card.className = "alert-card";
                card.onclick = () => selectAlert(alert.id);
                
                const time = new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                
                card.innerHTML = `
                    <div class="alert-card-header">
                        <span class="alert-card-title">${alert.site_name}</span>
                        <span class="alert-severity ${alert.severity.toLowerCase()}">${alert.severity}</span>
                    </div>
                    <p class="alert-summary">${alert.agent_summary}</p>
                    <div class="alert-meta">
                        <span><i class="fa-solid fa-location-dot"></i> [${alert.coordinates.latitude.toFixed(4)}, ${alert.coordinates.longitude.toFixed(4)}]</span>
                        <span>${time}</span>
                    </div>
                `;
                listContainer.appendChild(card);
                
                // Add marker to map
                L.marker([alert.coordinates.latitude, alert.coordinates.longitude])
                 .addTo(map)
                 .bindPopup(`<strong>${alert.site_name} Alert</strong><br>${alert.agent_summary}`);
            });
        } else {
            listContainer.innerHTML = `<div class="loading-spinner">No active encroachment alerts found.</div>`;
        }
    } catch (e) {
        listContainer.innerHTML = `<div class="loading-spinner" style="color: var(--alert-red);"><i class="fa-solid fa-circle-xmark"></i> Connection Error.</div>`;
    }
    updateLiveAnalytics();
}

// Select alert card
function selectAlert(alertId) {
    const alert = activeAlerts.find(a => a.id === alertId);
    if (!alert) return;

    // Pan map to alert location
    map.setView([alert.coordinates.latitude, alert.coordinates.longitude], 15);
    
    // Simulate/Load the scans
    loadScanResults({
        site_name: alert.site_name,
        baseline_rgb: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_')}_baseline_rgb.png`,
        current_rgb: alert.evidence_link,
        baseline_ndvi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_')}_baseline_ndvi.png`,
        current_ndvi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_')}_current_ndvi.png`,
        baseline_mndwi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_')}_baseline_mndwi.png`,
        current_mndwi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_')}_current_mndwi.png`,
    });
}

function loadScanResults(result) {
    lastScanResult = result;
    document.getElementById("current-comparison-site").innerText = result.site_name;
    updateComparisonImages();
}

// 5. Quick selects
function focusZone(siteName) {
    const zone = RISK_ZONES[siteName];
    if (zone) {
        map.setView([zone.lat, zone.lon], zone.zoom);
        zoneCircles[siteName].openPopup();
    }
}

// Trigger scan directly
async function triggerDirectScan(siteKey) {
    const zone = RISK_ZONES[siteKey];
    if (!zone) return;
    
    // Alert the chat
    appendMessage("user", `Inspect ${zone.name} coordinates.`);
    map.closePopup();
    
    executeAgentChat(`Scan coordinates latitude ${zone.lat} longitude ${zone.lon} for site name ${zone.name}`);
}

// 6. AI Agent Chat Interface
function setupChat() {
    const input = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send-btn");
    const traceHeader = document.querySelector(".trace-header");
    const traceLog = document.getElementById("trace-log");
    
    sendBtn.addEventListener("click", () => {
        const text = input.value.trim();
        if (!text) return;
        appendMessage("user", text);
        input.value = "";
        executeAgentChat(text);
    });

    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    traceHeader.addEventListener("click", () => {
        const isCollapsed = traceLog.style.display === "none";
        traceLog.style.display = isCollapsed ? "flex" : "none";
        document.querySelector(".toggle-trace-btn i").className = isCollapsed ? "fa-solid fa-chevron-up" : "fa-solid fa-chevron-down";
    });
}

function appendMessage(role, text) {
    const container = document.getElementById("chat-messages");
    
    // Remove typing indicator if present
    const existingIndicator = document.querySelector(".typing-indicator");
    if (existingIndicator) existingIndicator.remove();
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    
    // Format simple markdown bolding
    const formattedText = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

    bubble.innerHTML = `
        <div class="bubble-content">${formattedText}</div>
        <div class="bubble-meta">${role === 'user' ? 'You' : 'Agent'} • Just Now</div>
    `;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById("chat-messages");
    if (document.querySelector(".typing-indicator")) return;
    
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function appendTraceLog(type, content) {
    const trace = document.getElementById("trace-log");
    const entry = document.createElement("div");
    entry.className = `trace-entry ${type}`;
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.innerHTML = `[${time}] ${content}`;
    
    trace.appendChild(entry);
    trace.scrollTop = trace.scrollHeight;
}

// 7. Execute Chat call and Stream SSE response
async function executeAgentChat(messageText) {
    showTypingIndicator();
    appendTraceLog("system", `Sending prompt: "${messageText}"`);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: messageText,
                session_id: "be592cf8",
                user_id: "elikplim"
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        let agentText = "";
        let bubbleElement = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunkStr = decoder.decode(value);
            // Process lines (can contain multiple SSE events)
            const lines = chunkStr.split("\n\n");
            
            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const dataJson = JSON.parse(line.substring(6));
                    
                    // 1. Tool Call Spans
                    if (dataJson.function_calls && dataJson.function_calls.length > 0) {
                        dataJson.function_calls.forEach(fc => {
                            appendTraceLog("tool-call", `<i class="fa-solid fa-gear"></i> Calling <strong>${fc.name}</strong>: ${JSON.stringify(fc.args)}`);
                            
                            // Check if this was a scan zone tool call, pre-load images
                            if (fc.name === "scan_zone_tool") {
                                loadScanResults({
                                    site_name: fc.args.site_name || "Target Site",
                                    baseline_rgb: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_baseline_rgb.png`,
                                    current_rgb: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_current_rgb.png`,
                                    baseline_ndvi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_baseline_ndvi.png`,
                                    current_ndvi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_current_ndvi.png`,
                                    baseline_mndwi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_baseline_mndwi.png`,
                                    current_mndwi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_')}_current_mndwi.png`,
                                });
                            }
                        });
                    }
                    
                    // 2. Tool Response Spans
                    if (dataJson.function_responses && dataJson.function_responses.length > 0) {
                        dataJson.function_responses.forEach(fr => {
                            appendTraceLog("tool-response", `<i class="fa-solid fa-check"></i> <strong>${fr.name}</strong> returned: ${JSON.stringify(fr.response).substring(0, 100)}...`);
                            
                            // If scan completes, load real GEE results dynamically into the slider
                            if (fr.name === "scan_zone_tool") {
                                const scanData = fr.response;
                                if (scanData && scanData.status === "success") {
                                    loadScanResults(scanData);
                                    // Pan map to scanned coordinates dynamically
                                    if (scanData.latitude && scanData.longitude) {
                                        map.setView([scanData.latitude, scanData.longitude], 14);
                                    }
                                }
                                fetchAlerts();
                                updateLiveAnalytics();
                            } else if (fr.name === "send_alert_tool") {
                                fetchAlerts();
                                updateLiveAnalytics();
                            }
                        });
                    }

                    // 3. Text content updates
                    if (dataJson.text) {
                        // Remove typing indicator on first text segment
                        const existingIndicator = document.querySelector(".typing-indicator");
                        if (existingIndicator) existingIndicator.remove();

                        agentText += dataJson.text;
                        
                        if (!bubbleElement) {
                            bubbleElement = document.createElement("div");
                            bubbleElement.className = "chat-bubble agent";
                            document.getElementById("chat-messages").appendChild(bubbleElement);
                        }
                        
                        const formattedText = agentText
                            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                            .replace(/\*(.*?)\*/g, '<em>$1</em>')
                            .replace(/\n/g, '<br>');
                        
                        bubbleElement.innerHTML = `
                            <div class="bubble-content">${formattedText}</div>
                            <div class="bubble-meta">Agent • Streaming...</div>
                        `;
                        
                        const msgContainer = document.getElementById("chat-messages");
                        msgContainer.scrollTop = msgContainer.scrollHeight;
                    }
                    
                    if (dataJson.is_final && bubbleElement) {
                        bubbleElement.querySelector(".bubble-meta").innerText = "Agent • Just Now";
                        appendTraceLog("system", "Agent execution completed successfully.");
                    }
                }
            }
        }
    } catch (error) {
        console.error("Error reading stream:", error);
        appendTraceLog("system", `<span style="color: var(--alert-red);">Error: Failed to fetch stream.</span>`);
        const existingIndicator = document.querySelector(".typing-indicator");
        if (existingIndicator) existingIndicator.remove();
        appendMessage("agent", "I'm sorry, I encountered an error connecting to my backend agent runner. Please ensure the FastAPI server is running on port 8000.");
    }
}

// 8. Update Live Analytics Statistics
async function updateLiveAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/analytics`);
        const data = await response.json();
        
        document.getElementById("stat-alerts").innerText = data.total_alerts;
        document.getElementById("stat-scans").innerText = data.total_scans;
        document.getElementById("stat-success").innerText = data.success_rate;
    } catch (e) {
        console.error("Error updating live analytics:", e);
    }
}
