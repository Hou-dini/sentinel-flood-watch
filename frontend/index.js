// API Endpoint configuration
const API_BASE_URL = window.location.origin;

// Initialize unique Session ID using sessionStorage (persists across refresh in same tab)
let sessionId = sessionStorage.getItem("sentinel_session_id");
if (!sessionId) {
    sessionId = generateUUID();
    sessionStorage.setItem("sentinel_session_id", sessionId);
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}


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
    updateLegendOverlay(); // Initialize legend overlay
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
            updateLegendOverlay();
        });
    });
}

// Update the legend overlay descriptions and visual guides dynamically
function updateLegendOverlay() {
    const title = document.getElementById("legend-view-title");
    const desc = document.getElementById("legend-view-desc");
    const container = document.getElementById("legend-scale-container");
    
    if (!title || !desc || !container) return;
    
    if (currentActiveView === "rgb") {
        title.innerText = "True Color RGB";
        desc.innerText = "Natural color view (Red, Green, Blue bands). Highlights visible developments, vegetation clearings, and surface structures.";
        container.innerHTML = `
            <div class="legend-scale-item"><span class="color-dot rgb-green"></span><span>Forest/Vegetation</span></div>
            <div class="legend-scale-item"><span class="color-dot rgb-blue"></span><span>Water channels</span></div>
            <div class="legend-scale-item"><span class="color-dot rgb-grey"></span><span>Concrete/Buildings</span></div>
        `;
    } else if (currentActiveView === "ndvi") {
        title.innerText = "NDVI (Vegetation Index)";
        desc.innerText = "Normalized Difference Vegetation Index isolates plant health and canopy density. Stressed or cleared areas show up in red/yellow.";
        container.innerHTML = `
            <div class="legend-scale-item"><span class="color-dot ndvi-high"></span><span>Healthy Forest (NDVI > 0.4)</span></div>
            <div class="legend-scale-item"><span class="color-dot ndvi-med"></span><span>Cleared Land/Soil (NDVI 0.1 to 0.4)</span></div>
            <div class="legend-scale-item"><span class="color-dot ndvi-low"></span><span>Buildings/Encroachment (NDVI < 0.1)</span></div>
        `;
    } else if (currentActiveView === "mndwi") {
        title.innerText = "MNDWI (Water Index)";
        desc.innerText = "Modified Normalized Difference Water Index isolates open surface water (bright cyan). Narrowing indicates water blockage or siltation.";
        container.innerHTML = `
            <div class="legend-scale-item"><span class="color-dot mndwi-water"></span><span>Open Surface Water (MNDWI > 0.2)</span></div>
            <div class="legend-scale-item"><span class="color-dot mndwi-silt"></span><span>Wetlands/Siltation (MNDWI 0.0 to 0.2)</span></div>
            <div class="legend-scale-item"><span class="color-dot mndwi-land"></span><span>Dry Land/Concrete (MNDWI < 0.0)</span></div>
        `;
    }
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
        baseline_rgb: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_rgb.png`,
        current_rgb: alert.evidence_link,
        baseline_ndvi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_ndvi.png`,
        current_ndvi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_current_ndvi.png`,
        baseline_mndwi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_mndwi.png`,
        current_mndwi: `/static/mock_${alert.site_name.toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_current_mndwi.png`,
    });
}

function loadScanResults(result) {
    lastScanResult = result;
    document.getElementById("current-comparison-site").innerText = result.site_name;

    // Update slider labels with actual acquisition dates
    const baselineLabel = document.getElementById("label-baseline");
    const currentLabel = document.getElementById("label-current");
    if (result.baseline_date && result.baseline_date !== "N/A") {
        baselineLabel.innerText = `Baseline — ${result.baseline_date}`;
    } else {
        baselineLabel.innerText = "Baseline (Historical)";
    }
    if (result.current_date && result.current_date !== "N/A") {
        currentLabel.innerText = `Current — ${result.current_date}`;
    } else {
        currentLabel.innerText = "Current (Satellite Scan)";
    }

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

// Render markdown to HTML safely using marked library
if (typeof marked !== 'undefined' && marked.use) {
    marked.use({ breaks: true });
}

function renderMarkdown(text) {
    if (typeof marked !== 'undefined' && marked.parse) {
        return marked.parse(text);
    }
    // Fallback if marked library fails to load
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

/**
 * Detects when the agent returns a structured JSON response wrapped in a
 * markdown fenced code block (```json ... ```) or raw JSON array/object.
 *
 * Returns an object with:
 *   { isStructured: true,  summary: string, json: object }  — on success
 *   { isStructured: false }                                  — plain markdown
 */
function parseAgentJsonResponse(text) {
    const trimmed = text.trim();

    // 1. Try to find a ```json ... ``` code fence (case-insensitive)
    let fenceMatch = trimmed.match(/```json\s*([\s\S]*?)\s*```/i);
    let jsonString = null;
    let nonJsonText = "";

    if (fenceMatch) {
        jsonString = fenceMatch[1].trim();
        const fenceIndex = trimmed.indexOf(fenceMatch[0]);
        const beforeText = trimmed.substring(0, fenceIndex).trim();
        const afterText = trimmed.substring(fenceIndex + fenceMatch[0].length).trim();
        nonJsonText = [beforeText, afterText].filter(t => t).join("\n\n");
    } else {
        // Try general ``` ... ``` code fence
        fenceMatch = trimmed.match(/```\s*([\s\S]*?)\s*```/);
        if (fenceMatch) {
            jsonString = fenceMatch[1].trim();
            const fenceIndex = trimmed.indexOf(fenceMatch[0]);
            const beforeText = trimmed.substring(0, fenceIndex).trim();
            const afterText = trimmed.substring(fenceIndex + fenceMatch[0].length).trim();
            nonJsonText = [beforeText, afterText].filter(t => t).join("\n\n");
        } else {
            // 2. Try to locate the first '{' or '[' and last '}' or ']' to extract raw JSON
            const startIdxObj = trimmed.indexOf('{');
            const startIdxArr = trimmed.indexOf('[');
            let startIdx = -1;
            let endIdx = -1;
            
            if (startIdxObj !== -1 && startIdxArr !== -1) {
                startIdx = Math.min(startIdxObj, startIdxArr);
            } else {
                startIdx = startIdxObj !== -1 ? startIdxObj : startIdxArr;
            }
            
            if (startIdx !== -1) {
                if (startIdx === startIdxObj) {
                    endIdx = trimmed.lastIndexOf('}');
                } else {
                    endIdx = trimmed.lastIndexOf(']');
                }
            }
            
            if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
                jsonString = trimmed.substring(startIdx, endIdx + 1);
                const beforeText = trimmed.substring(0, startIdx).trim();
                const afterText = trimmed.substring(endIdx + 1).trim();
                nonJsonText = [beforeText, afterText].filter(t => t).join("\n\n");
            }
        }
    }

    if (jsonString) {
        try {
            const parsed = JSON.parse(jsonString);
            if (parsed && (typeof parsed === 'object' || Array.isArray(parsed))) {
                let summary = nonJsonText;
                if (!summary) {
                    if (Array.isArray(parsed)) {
                        summary = `Retrieved list of ${parsed.length} items.`;
                    } else if (parsed.agent_summary) {
                        summary = parsed.agent_summary;
                    } else if (parsed.message) {
                        summary = parsed.message;
                    } else {
                        summary = "Structured data response:";
                    }
                }
                return { isStructured: true, summary: summary, json: parsed };
            }
        } catch (_) {
            // Ignore parse errors and fall through
        }
    }

    return { isStructured: false };
}

/**
 * Builds the inner HTML for a structured agent response bubble.
 * Renders agent_summary or non-JSON context as prose and the full JSON as a collapsible
 * <details> block so the user can inspect the raw schema if needed.
 */
/**
 * Helper to split and parse narrative text and actions list.
 */
function parseReportText(text) {
    let narrative = text;
    let actions = [];
    
    const actionDelimiter = /DATABASE & NOTIFICATION ACTIONS:|DATABASE & NOTIFICATIONS:|ACTIONS EXECUTED:/i;
    const parts = text.split(actionDelimiter);
    
    const checkFailure = (str) => {
        const lower = str.toLowerCase();
        return lower.includes("fail") || 
               lower.includes("error") || 
               lower.includes("unreachable") || 
               lower.includes("unable") || 
               lower.includes("could not") || 
               lower.includes("cannot") ||
               lower.includes("refuse") ||
               lower.includes("denied");
    };

    if (parts.length > 1) {
        narrative = parts[0].trim();
        const actionsSection = parts[1].trim();
        const actionLines = actionsSection.split(/\r?\n/);
        for (let line of actionLines) {
            line = line.trim();
            if (!line) continue;
            const cleanLine = line.replace(/^[0-9]+\.\s*|^-\s*/, '').trim();
            if (cleanLine) {
                actions.push({
                    text: cleanLine,
                    status: checkFailure(cleanLine) ? 'failure' : 'success'
                });
            }
        }
    } else {
        // No explicit header. Split the narrative into sentences and extract database/SMS logs.
        // Splits sentences by period followed by space.
        const sentences = narrative.split(/(?<=\.)\s+/);
        const remainingSentences = [];
        
        for (let sentence of sentences) {
            sentence = sentence.trim();
            if (!sentence) continue;
            
            const isDbAction = sentence.toLowerCase().includes("database") || 
                               sentence.toLowerCase().includes("logged in the") ||
                               sentence.toLowerCase().includes("inserted successfully") ||
                               sentence.toLowerCase().includes("logged into the");
                               
            const isSmsAction = sentence.toLowerCase().includes("sms") || 
                                sentence.toLowerCase().includes("twilio") ||
                                sentence.toLowerCase().includes("dispatched to") ||
                                sentence.toLowerCase().includes("notification was immediately");
                                
            if (isDbAction || isSmsAction) {
                actions.push({
                    text: sentence,
                    status: checkFailure(sentence) ? 'failure' : 'success'
                });
            } else {
                remainingSentences.push(sentence);
            }
        }
        
        if (actions.length > 0) {
            narrative = remainingSentences.join(" ");
        }
    }
    
    narrative = narrative.replace(/^ECOLOGICAL MONITORING REPORT:\s*/i, '').trim();
    return { narrative, actions };
}

/**
 * Extract NDVI and MNDWI metrics from narrative.
 */
function extractMetrics(text) {
    const metrics = { ndvi: null, mndwi: null };
    
    // NDVI Match
    const ndviMatch = text.match(/NDVI[^\n]*?changed\s+by\s+([+-]?[0-9.]+)%\s*\(from\s+([0-9.-]+)\s+to\s+([0-9.-]+)\)/i)
                   || text.match(/NDVI[^\n]*?from\s+([0-9.-]+)\s+to\s+([0-9.-]+)/i);
    if (ndviMatch) {
        if (ndviMatch.length === 4) {
            metrics.ndvi = {
                change: parseFloat(ndviMatch[1]),
                from: parseFloat(ndviMatch[2]),
                to: parseFloat(ndviMatch[3]),
                hasChangePct: true
            };
        } else {
            const from = parseFloat(ndviMatch[1]);
            const to = parseFloat(ndviMatch[2]);
            metrics.ndvi = {
                change: -((from - to) * 100),
                from: from,
                to: to,
                hasChangePct: false
            };
        }
    } else {
        const ndviPctMatch = text.match(/NDVI[^\n]*?(?:loss|decrease|narrowing)[^\n]*?(\d+)%/i);
        if (ndviPctMatch) {
            metrics.ndvi = {
                change: -parseFloat(ndviPctMatch[1]),
                hasChangePct: true
            };
        }
    }
    
    // MNDWI Match
    const mndwiMatch = text.match(/MNDWI[^\n]*?changed\s+by\s+([+-]?[0-9.]+)%\s*\(from\s+([0-9.-]+)\s+to\s+([0-9.-]+)\)/i)
                    || text.match(/MNDWI[^\n]*?from\s+([0-9.-]+)\s+to\s+([0-9.-]+)\)/i)
                    || text.match(/MNDWI[^\n]*?from\s+([0-9.-]+)\s+to\s+([0-9.-]+)/i);
    if (mndwiMatch) {
        if (mndwiMatch.length === 4) {
            metrics.mndwi = {
                change: parseFloat(mndwiMatch[1]),
                from: parseFloat(mndwiMatch[2]),
                to: parseFloat(mndwiMatch[3]),
                hasChangePct: true
            };
        } else {
            const from = parseFloat(mndwiMatch[1]);
            const to = parseFloat(mndwiMatch[2]);
            metrics.mndwi = {
                change: -((from - to) * 100),
                from: from,
                to: to,
                hasChangePct: false
            };
        }
    } else {
        const mndwiPctMatch = text.match(/MNDWI[^\n]*?(?:loss|decrease|narrowing)[^\n]*?(\d+)%/i);
        if (mndwiPctMatch) {
            metrics.mndwi = {
                change: -parseFloat(mndwiPctMatch[1]),
                hasChangePct: true
            };
        }
    }
    
    return metrics;
}

/**
 * Builds the inner HTML for a structured agent response bubble.
 * Renders agent_summary or non-JSON context as prose and the full JSON as a collapsible
 * <details> block so the user can inspect the raw schema if needed.
 */
function buildStructuredBubble(parsed) {
    const json = parsed.json;
    
    const hasReport = json.site_name && json.site_name !== "N/A" && json.site_name !== "None";
    const isRefusal = !hasReport && 
                      (parsed.summary.toLowerCase().includes("refuse") || 
                       parsed.summary.toLowerCase().includes("unauthorized request"));
                      
    if (isRefusal) {
        return `
            <div class="refusal-card">
                <div class="refusal-header">
                    <i class="fa-solid fa-shield-halved text-red"></i>
                    <span>Security Policy Refusal</span>
                </div>
                <div class="refusal-text">${renderMarkdown(parsed.summary)}</div>
            </div>
        `;
    }
    
    // If it's a standard ecological report
    if (json.site_name && json.agent_summary) {
        const { narrative, actions } = parseReportText(json.agent_summary);
        const metrics = extractMetrics(json.agent_summary);
        
        let severityClass = (json.severity || "low").toLowerCase();
        
        let coordsText = "N/A";
        if (json.coordinates && json.coordinates.latitude !== undefined) {
            coordsText = `[${json.coordinates.latitude.toFixed(4)}, ${json.coordinates.longitude.toFixed(4)}]`;
        }
        
        // Build metrics HTML
        let metricsHtml = "";
        if (metrics.ndvi || metrics.mndwi) {
            metricsHtml = `<div class="metrics-grid">`;
            
            if (metrics.ndvi) {
                const isDecreasing = metrics.ndvi.to !== undefined ? metrics.ndvi.to < metrics.ndvi.from : metrics.ndvi.change < 0;
                const trendIcon = isDecreasing 
                    ? `<i class="fa-solid fa-arrow-trend-down text-red"></i>`
                    : `<i class="fa-solid fa-arrow-trend-up text-green"></i>`;
                const trendText = isDecreasing ? "Vegetation Loss" : "Vegetation Stable";
                const changeSign = metrics.ndvi.change > 0 ? "+" : "";
                const changeVal = metrics.ndvi.change !== undefined ? `${changeSign}${metrics.ndvi.change.toFixed(1)}%` : "";
                
                metricsHtml += `
                    <div class="metric-card ${isDecreasing && json.severity !== 'Low' ? 'alert-border' : ''}">
                        <div class="metric-header">
                            ${trendIcon}
                            <span>NDVI (Vegetation Index)</span>
                        </div>
                        <div class="metric-value-row">
                            <span class="metric-val">${metrics.ndvi.to !== undefined ? metrics.ndvi.to.toFixed(3) : changeVal}</span>
                            ${metrics.ndvi.from !== undefined ? `<span class="metric-change-label">from ${metrics.ndvi.from.toFixed(3)}</span>` : ''}
                        </div>
                        <div class="metric-trend ${isDecreasing && json.severity !== 'Low' ? 'text-red' : 'text-green'}">
                            ${trendText} ${changeVal ? `(${changeVal})` : ''}
                        </div>
                    </div>
                `;
            }
            
            if (metrics.mndwi) {
                // If MNDWI increases (becomes less negative), it denotes water index increase, i.e. water channel alteration
                const isAltered = metrics.mndwi.to !== undefined ? metrics.mndwi.to > metrics.mndwi.from : metrics.mndwi.change < 0;
                const trendIcon = isAltered 
                    ? `<i class="fa-solid fa-water text-red"></i>`
                    : `<i class="fa-solid fa-water text-green"></i>`;
                const trendText = isAltered ? "Channel Altered" : "Water Stable";
                const changeSign = metrics.mndwi.change > 0 ? "+" : "";
                const changeVal = metrics.mndwi.change !== undefined ? `${changeSign}${metrics.mndwi.change.toFixed(1)}%` : "";
                
                metricsHtml += `
                    <div class="metric-card ${isAltered && json.severity !== 'Low' ? 'alert-border' : ''}">
                        <div class="metric-header">
                            ${trendIcon}
                            <span>MNDWI (Water Index)</span>
                        </div>
                        <div class="metric-value-row">
                            <span class="metric-val">${metrics.mndwi.to !== undefined ? metrics.mndwi.to.toFixed(3) : changeVal}</span>
                            ${metrics.mndwi.from !== undefined ? `<span class="metric-change-label">from ${metrics.mndwi.from.toFixed(3)}</span>` : ''}
                        </div>
                        <div class="metric-trend ${isAltered && json.severity !== 'Low' ? 'text-red' : 'text-green'}">
                            ${trendText} ${changeVal ? `(${changeVal})` : ''}
                        </div>
                    </div>
                `;
            }
            
            metricsHtml += `</div>`;
        }
        
        // Build actions HTML
        let actionsHtml = "";
        if (actions.length > 0) {
            actionsHtml = `
                <div class="actions-log">
                    <div class="actions-title">Actions Executed</div>
                    ${actions.map(action => {
                        const iconClass = action.status === 'failure' 
                            ? 'fa-solid fa-circle-xmark text-red' 
                            : 'fa-solid fa-circle-check text-green';
                        return `
                            <div class="action-item">
                                <i class="${iconClass}"></i>
                                <span>${action.text}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
        
        // Collapsible RAW data
        let detailRows = Object.entries(json)
            .filter(([k]) => k !== 'agent_summary')
            .map(([k, v]) => {
                const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                let valStr = typeof v === 'object' ? JSON.stringify(v) : String(v);
                return `<tr><td class="json-key">${label}</td><td class="json-val">${valStr}</td></tr>`;
            }).join('');
            
        // Check if there is warning/refusal text outside the JSON block
        let warningBannerHtml = "";
        const containsRefusal = parsed.summary && 
                                (parsed.summary.toLowerCase().includes("refuse") || 
                                 parsed.summary.toLowerCase().includes("unauthorized request"));
        if (containsRefusal && parsed.summary !== json.agent_summary) {
            warningBannerHtml = `
                <div class="report-warning-banner">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span>${renderMarkdown(parsed.summary)}</span>
                </div>
            `;
        }
            
        return `
            <div class="report-card">
                ${warningBannerHtml}
                <div class="report-header">
                    <div class="report-title-section">
                        <div class="report-title">
                            <i class="fa-solid fa-square-poll-vertical text-cyan"></i>
                            <span>Sentinel Scan Report</span>
                        </div>
                        <div class="report-subtitle">${json.site_name} &nbsp;•&nbsp; ${coordsText}</div>
                    </div>
                    <div class="badge-row">
                        <span class="alert-severity ${severityClass}">${json.severity || 'Low'}</span>
                    </div>
                </div>
                
                ${metricsHtml}
                
                <div class="report-narrative">${renderMarkdown(narrative)}</div>
                
                ${actionsHtml}
                
                <details class="agent-json-details">
                    <summary>View structured data</summary>
                    <table class="agent-json-table"><tbody>${detailRows}</tbody></table>
                </details>
            </div>
        `;
    }
    
    // Fallback if not standard report structure
    let detailRows = "";
    const formatValue = (v) => {
        if (v === null || v === undefined) return "<em>null</em>";
        if (typeof v === 'object') {
            return `<pre style="margin: 0; font-family: inherit; font-size: inherit; white-space: pre-wrap; background: rgba(0,0,0,0.1); padding: 4px; border-radius: 4px;">${JSON.stringify(v, null, 2)}</pre>`;
        }
        return String(v);
    };

    if (Array.isArray(parsed.json)) {
        detailRows = parsed.json.map((item, idx) => {
            if (item && typeof item === 'object' && !Array.isArray(item)) {
                const itemRows = Object.entries(item)
                    .map(([k, v]) => {
                        const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                        return `<tr><td class="json-key" style="padding-left: 20px;">${label}</td><td class="json-val">${formatValue(v)}</td></tr>`;
                    }).join('');
                return `
                    <tr><td colspan="2" class="json-key" style="background: rgba(255,255,255,0.02); font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 8px 12px;">Item #${idx + 1}</td></tr>
                    ${itemRows}
                `;
            } else {
                return `<tr><td class="json-key">Item #${idx + 1}</td><td class="json-val">${formatValue(item)}</td></tr>`;
            }
        }).join('');
    } else {
        const filterKey = parsed.summary === parsed.json.agent_summary ? 'agent_summary' : null;
        detailRows = Object.entries(parsed.json)
            .filter(([k]) => k !== filterKey)
            .map(([k, v]) => {
                const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                return `<tr><td class="json-key">${label}</td><td class="json-val">${formatValue(v)}</td></tr>`;
            }).join('');
    }

    return `
        <div class="bubble-content">${renderMarkdown(parsed.summary)}</div>
        <details class="agent-json-details">
            <summary>View structured data</summary>
            <table class="agent-json-table"><tbody>${detailRows}</tbody></table>
        </details>
    `;
}

function appendMessage(role, text) {
    const container = document.getElementById("chat-messages");
    
    // Remove typing indicator if present
    const existingIndicator = document.querySelector(".typing-indicator");
    if (existingIndicator) existingIndicator.remove();
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    
    if (role === 'agent') {
        const parsed = parseAgentJsonResponse(text);
        if (parsed.isStructured) {
            bubble.innerHTML = `
                ${buildStructuredBubble(parsed)}
                <div class="bubble-meta">Agent • Just Now</div>
            `;
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
            return;
        }
    }

    const formattedText = renderMarkdown(text);

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
                session_id: sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        
        let agentText = "";
        let bubbleElement = null;
        let buffer = ""; // Store incomplete data across reads

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            
            // Split by double newline (standard SSE event delimiter)
            const parts = buffer.split("\n\n");
            
            // The last part is either incomplete or an empty string after the trailing \n\n
            buffer = parts.pop();
            
            for (const part of parts) {
                const line = part.trim();
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
                                    baseline_rgb: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_rgb.png`,
                                    current_rgb: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_current_rgb.png`,
                                    baseline_ndvi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_ndvi.png`,
                                    current_ndvi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_current_ndvi.png`,
                                    baseline_mndwi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_baseline_mndwi.png`,
                                    current_mndwi: `/static/mock_${(fc.args.site_name || 'site').toLowerCase().replace(/ /g, '_').replace(/\//g, '_')}_current_mndwi.png`,
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

                        // While streaming, render markdown as usual (the JSON fence
                        // arrives as one final chunk so streaming looks normal).
                        // On the final event we re-render with the structured parser.
                        const formattedText = renderMarkdown(agentText);
                        bubbleElement.innerHTML = `
                            <div class="bubble-content">${formattedText}</div>
                            <div class="bubble-meta">Agent • Streaming...</div>
                        `;
                        
                        const msgContainer = document.getElementById("chat-messages");
                        msgContainer.scrollTop = msgContainer.scrollHeight;
                    }
                    
                    if (dataJson.is_final && bubbleElement) {
                        // Re-parse the complete accumulated text. If the agent
                        // returned a structured JSON block, render it as a
                        // human-readable summary + collapsible details panel.
                        const parsed = parseAgentJsonResponse(agentText);
                        if (parsed.isStructured) {
                            bubbleElement.innerHTML =
                                buildStructuredBubble(parsed) +
                                `<div class="bubble-meta">Agent • Just Now</div>`;
                            bubbleElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                            bubbleElement.querySelector(".bubble-meta").innerText = "Agent • Just Now";
                        }
                        appendTraceLog("system", "Agent execution completed successfully.");
                    }
                }
            }
        }

        // Final fallback: if the stream closed but the bubble remains in "Streaming..." state, format it
        if (bubbleElement && bubbleElement.querySelector(".bubble-meta") && bubbleElement.querySelector(".bubble-meta").innerText === "Agent • Streaming...") {
            const parsed = parseAgentJsonResponse(agentText);
            if (parsed.isStructured) {
                bubbleElement.innerHTML =
                    buildStructuredBubble(parsed) +
                    `<div class="bubble-meta">Agent • Just Now</div>`;
                bubbleElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                bubbleElement.querySelector(".bubble-meta").innerText = "Agent • Just Now";
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
