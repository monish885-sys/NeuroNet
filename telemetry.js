// Initialize the session data array
let sessionData = [];
const SESSION_ID = `session_${Date.now()}`;

// --- MOUSE MOVEMENT TRACKING (with throttling) ---
let mouseMoveTimeout;
document.addEventListener('mousemove', (event) => {
    // This clears the previous timeout, so we only log the last event every 100ms
    clearTimeout(mouseMoveTimeout);
    mouseMoveTimeout = setTimeout(() => {
        logEvent('mousemove', { x: event.clientX, y: event.clientY });
    }, 100); // Throttle to 100ms
});

// --- TAB FOCUS TRACKING ---
window.addEventListener('focus', () => logEvent('tab_focus', { status: 'focused' }));
window.addEventListener('blur', () => logEvent('tab_focus', { status: 'blurred' }));

// --- TYPING BEHAVIOR TRACKING ---
// Find all input fields we want to track
const trackedInputs = document.querySelectorAll('.tracked-input');
trackedInputs.forEach(input => {
    input.addEventListener('keydown', (event) => {
        logEvent('keydown', { inputId: input.id, key: event.key });
    });
});

/**
 * A helper function to log an event with a timestamp and save it.
 * @param {string} type - The type of event (e.g., 'mousemove').
 * @param {object} details - The specific details of the event.
 */
function logEvent(type, details) {
    const eventLog = {
        type: type,
        timestamp: new Date().toISOString(),
        details: details
    };
    
    sessionData.push(eventLog);
    
    // Save the updated array to localStorage
    localStorage.setItem(SESSION_ID, JSON.stringify(sessionData));
    
    // Log to console for real-time viewing
    console.log('Event Logged:', eventLog);
}

// Initial log to mark the session start
console.log(`Telemetry tracking started for session: ${SESSION_ID}`);
logEvent('session_start', { userAgent: navigator.userAgent });