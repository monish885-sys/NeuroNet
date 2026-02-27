/**
 * Client-side summarization: only distilled counts are sent (Data Minimization).
 * Raw mouse coordinates and event details never leave the browser.
 */

const API_BASE = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    const popupContainer = document.getElementById('popup-container');
    const insightTextElement = document.getElementById('insight-text');
    const closePopupButton = document.getElementById('close-popup');
    const analyzeButton = document.getElementById('analyze-btn');
    const dashboard = window.neuronetDashboard;

    analyzeButton.addEventListener('click', runAnalysis);
    closePopupButton.addEventListener('click', () => {
        popupContainer.classList.add('hidden');
    });

    async function runAnalysis() {
        if (!dashboard) return;
        dashboard.setStep('data_received', false);
        dashboard.setStep('insight_generated', false);
        dashboard.setStep('raw_data_shredded', false);
        dashboard.setStep('hash_created', false);

        const storedData = localStorage.getItem(SESSION_ID);
        if (!storedData) {
            insightTextElement.textContent = 'No session data found. Use the quiz first.';
            popupContainer.classList.remove('hidden');
            return;
        }

        const behavioralData = JSON.parse(storedData);
        // Data minimization: compute only distilled summary (no raw coords, no event details)
        const summary = buildDistilledSummary(behavioralData);

        analyzeButton.classList.add('loading');
        analyzeButton.disabled = true;
        dashboard.setStep('data_received', true);

        try {
            const response = await fetch(`${API_BASE}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(summary),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok.');
            }

            const result = await response.json();
            dashboard.setStep('insight_generated', true);
            dashboard.setStep('raw_data_shredded', true);
            if (result.verification_certificate && result.verification_certificate.hash) {
                dashboard.setVerificationHash(result.verification_certificate.hash);
                dashboard.setStep('hash_created', true);
            }

            const insight = result.insight || result.error || 'No insight returned.';
            insightTextElement.textContent = insight;
            popupContainer.classList.remove('hidden');
        } catch (error) {
            console.error('Error during analysis:', error);
            insightTextElement.textContent = 'An error occurred during analysis. Please check the console.';
            popupContainer.classList.remove('hidden');
        } finally {
            analyzeButton.classList.remove('loading');
            analyzeButton.disabled = false;
        }
    }
});

/**
 * Build a minimal summary for the backend. Raw mouse positions and event details
 * are never included — only counts and session duration (Data Minimization).
 */
function buildDistilledSummary(events) {
    const tabSwitchCount = events.filter(e => e.type === 'tab_focus').length;
    const keystrokeCount = events.filter(e => e.type === 'keydown').length;
    const firstTs = events.length ? new Date(events[0].timestamp).getTime() : 0;
    const lastTs = events.length ? new Date(events[events.length - 1].timestamp).getTime() : 0;
    const sessionDurationSeconds = (lastTs - firstTs) / 1000;

    return {
        tab_switch_count: tabSwitchCount,
        keystroke_count: keystrokeCount,
        total_events: events.length,
        session_duration_seconds: sessionDurationSeconds,
    };
}
