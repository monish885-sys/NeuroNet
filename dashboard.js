/**
 * Transparency Dashboard: real-time status for Data Received → Insight → Shredded → Hash
 */
(function () {
    const steps = [
        { id: 'data_received', label: 'Data Received' },
        { id: 'insight_generated', label: 'Insight Generated' },
        { id: 'raw_data_shredded', label: 'Raw Data Shredded' },
        { id: 'hash_created', label: 'Verification Hash Created' },
    ];

    function render() {
        const container = document.getElementById('transparency-dashboard');
        if (!container) return;
        container.innerHTML = steps
            .map(
                (s) =>
                    `<div class="dashboard-step" data-step="${s.id}">
            <span class="step-indicator pending"></span>
            <span class="step-label">${s.label}</span>
            ${s.id === 'hash_created' ? '<code class="step-hash" id="dashboard-hash">—</code>' : ''}
          </div>`
            )
            .join('');
    }

    function setStep(stepId, done) {
        const el = document.querySelector(`[data-step="${stepId}"]`);
        if (!el) return;
        const ind = el.querySelector('.step-indicator');
        if (ind) {
            ind.classList.toggle('done', !!done);
            ind.classList.toggle('pending', !done);
        }
    }

    function setVerificationHash(hash) {
        const el = document.getElementById('dashboard-hash');
        if (el) el.textContent = hash ? hash.slice(0, 16) + '…' : '—';
    }

    function init() {
        render();
        var privacyBtn = document.getElementById('privacy-mode-btn');
        var privacyModal = document.getElementById('privacy-modal');
        var closePrivacy = document.getElementById('close-privacy-modal');
        if (privacyBtn && privacyModal) {
            privacyBtn.addEventListener('click', function () {
                privacyModal.classList.remove('hidden');
                privacyModal.setAttribute('aria-hidden', 'false');
            });
        }
        if (closePrivacy && privacyModal) {
            closePrivacy.addEventListener('click', function () {
                privacyModal.classList.add('hidden');
                privacyModal.setAttribute('aria-hidden', 'true');
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.neuronetDashboard = {
        setStep,
        setVerificationHash,
    };
})();
