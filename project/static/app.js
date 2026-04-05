const statusBadge = document.getElementById('status-badge');
const cloudBanner = document.getElementById('cloud-banner');
const cloudDest = document.getElementById('cloud-dest');
const noBackend = document.getElementById('no-backend');
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const loading = document.getElementById('loading');
const responsesDiv = document.getElementById('responses');

let backendAvailable = false;
let currentBackendName = '';
let cloudConfirmed = true;

async function checkStatus() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();

        cloudConfirmed = data.cloud_confirmed !== false;

        if (data.backend) {
            let msg = data.message;
            if (data.verifier_backend) {
                msg += ` | verifier: ${data.verifier_backend} (${data.verifier_model})`;
            }
            statusBadge.textContent = msg;
            statusBadge.className = 'online';
            backendAvailable = true;
            currentBackendName = data.backend;
            noBackend.classList.remove('visible');
            queryInput.disabled = false;
            submitBtn.disabled = false;

            if (data.backend === 'claude' || data.backend === 'openrouter') {
                cloudBanner.classList.add('visible');
                const destMap = {
                    'claude': 'api.anthropic.com',
                    'openrouter': 'openrouter.ai'
                };
                cloudDest.textContent = destMap[data.backend] || 'an external API';

                // Show cloud gate if not yet confirmed
                const gateEl = document.getElementById('cloud-gate');
                if (gateEl && !cloudConfirmed) {
                    gateEl.classList.add('visible');
                    queryInput.disabled = true;
                    submitBtn.disabled = true;
                } else if (gateEl) {
                    gateEl.classList.remove('visible');
                }
            } else {
                cloudBanner.classList.remove('visible');
                const gateEl = document.getElementById('cloud-gate');
                if (gateEl) gateEl.classList.remove('visible');
            }
        } else {
            statusBadge.textContent = 'No backend';
            statusBadge.className = 'offline';
            backendAvailable = false;
            noBackend.classList.add('visible');
            queryInput.disabled = true;
            submitBtn.disabled = true;
        }
    } catch {
        statusBadge.textContent = 'Error';
        statusBadge.className = 'offline';
    }
}

async function confirmCloud() {
    try {
        const resp = await fetch('/api/cloud/confirm', { method: 'POST' });
        if (resp.ok) {
            cloudConfirmed = true;
            const gateEl = document.getElementById('cloud-gate');
            if (gateEl) gateEl.classList.remove('visible');
            queryInput.disabled = false;
            submitBtn.disabled = false;
            await checkStatus();
        }
    } catch (err) {
        alert('Failed to confirm cloud access: ' + err.message);
    }
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatMs(ms) {
    if (ms < 1000) return ms + 'ms';
    return (ms / 1000).toFixed(1) + 's';
}

function isLocalDest(dest) {
    return dest.startsWith('local/');
}

function renderAuditTimeline(auditTrail) {
    if (!auditTrail || auditTrail.length === 0) {
        return '<p style="color: var(--text-muted); font-size: 12px; padding: 8px;">No operations recorded</p>';
    }

    return auditTrail.map(event => {
        const local = isLocalDest(event.destination);
        const dotClass = local ? 'local' : 'external';
        const chainTag = event.chain_hash ? event.chain_hash.substring(0, 12) : '';
        const isFailed = event.destination === 'error';
        const failedClass = isFailed ? ' failed' : '';

        return `
            <div class="audit-event${failedClass}">
                <span class="audit-dot ${isFailed ? 'error' : dotClass}"></span>
                <div class="audit-info">
                    <div class="audit-desc">${esc(event.description)}</div>
                    <div class="audit-meta">
                        <span>${formatMs(event.latency_ms)}</span>
                        <span>${esc(event.destination)}</span>
                        <span>#${esc(event.content_hash ? event.content_hash.substring(0, 16) : '')}</span>
                    </div>
                    <div class="audit-data-flow">
                        <span class="data-flow-arrow outbound">&uarr; ${formatBytes(event.bytes_sent)}</span>
                        <span class="data-flow-arrow inbound">&darr; ${formatBytes(event.bytes_received)}</span>
                        ${chainTag ? `<span class="chain-link" title="Provenance chain hash">&#x1f517;${esc(chainTag)}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function exportBundle(responseId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Exporting...';
    try {
        const resp = await fetch(`/api/response/${responseId}/bundle`);
        const bundle = await resp.json();
        const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `glass-proof-${responseId.substring(0, 8)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        btnEl.textContent = 'Exported';
        btnEl.className = 'bundle-export-btn exported';
        setTimeout(() => {
            btnEl.textContent = 'Export Proof';
            btnEl.className = 'bundle-export-btn';
            btnEl.disabled = false;
        }, 2000);
    } catch (err) {
        btnEl.textContent = 'Error';
        btnEl.disabled = false;
    }
}

async function verifySeal(responseId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Checking...';
    try {
        const resp = await fetch(`/api/response/${responseId}/verify`);
        const result = await resp.json();
        const sealEl = document.getElementById('seal-status-' + responseId);
        // Support both old "verified" field name and new "chain_intact"
        const isIntact = result.chain_intact !== undefined ? result.chain_intact : result.verified;
        if (isIntact) {
            sealEl.className = 'seal-status intact';
            sealEl.textContent = 'Chain intact — ' + result.events_checked + ' events checked';
            btnEl.textContent = 'Chain Intact';
            btnEl.className = 'seal-verify-btn intact';
        } else {
            sealEl.className = 'seal-status broken';
            sealEl.textContent = 'CHAIN BROKEN — ' + result.message;
            btnEl.textContent = 'Failed';
            btnEl.className = 'seal-verify-btn broken';
        }
    } catch (err) {
        btnEl.textContent = 'Error';
    }
}

function renderResponse(data) {
    const consistent = data.claims.filter(c => c.status === 'consistent').length;
    // Support legacy "verified" status from older stored responses
    const consistentLegacy = data.claims.filter(c => c.status === 'verified').length;
    const totalConsistent = consistent + consistentLegacy;
    const uncertain = data.claims.filter(c => c.status === 'uncertain').length;
    const unverifiable = data.claims.filter(c => c.status === 'unverifiable').length;

    const totalLatency = data.audit_trail.reduce((s, e) => s + e.latency_ms, 0);
    const totalSent = data.audit_trail.reduce((s, e) => s + e.bytes_sent, 0);
    const totalReceived = data.audit_trail.reduce((s, e) => s + e.bytes_received, 0);
    const externalCalls = data.audit_trail.filter(e => !isLocalDest(e.destination)).length;

    const premiseHtml = data.premise_flags.length > 0
        ? `<div class="premise-flags">
            <h3>Premise issues detected in your query:</h3>
            <ul>${data.premise_flags.map(f => '<li>' + esc(f) + '</li>').join('')}</ul>
           </div>`
        : '';

    // Normalize legacy "verified" status to "consistent" for display
    const normalizeStatus = (s) => s === 'verified' ? 'consistent' : s;

    const claimsHtml = data.claims.map((claim) => {
        const displayStatus = normalizeStatus(claim.status);
        return `
        <div class="claim ${displayStatus}" onclick="this.classList.toggle('expanded')">
            <div class="claim-text">
                <span class="claim-status ${displayStatus}">${displayStatus}</span>
                <span>${esc(claim.text)}</span>
            </div>
            <div class="claim-evidence">${esc(claim.evidence)}</div>
        </div>
        `;
    }).join('');

    const responseId = data.id;
    const reasoningId = 'reason-' + responseId;
    const sealDisplay = data.provenance_seal ? data.provenance_seal.substring(0, 16) + '...' : 'none';

    const html = `
        <div class="response">
            <div class="response-header">
                <div class="response-header-left">
                    <div class="verification-summary">
                        <span class="count"><span class="dot consistent"></span> ${totalConsistent} consistent</span>
                        <span class="count"><span class="dot uncertain"></span> ${uncertain} uncertain</span>
                        <span class="count"><span class="dot unverifiable"></span> ${unverifiable} unverifiable</span>
                    </div>
                    <div class="pipeline-summary">
                        <span class="ps-item">Pipeline: <span class="ps-value">${formatMs(totalLatency)}</span></span>
                        <span class="ps-item">&uarr; <span class="ps-value">${formatBytes(totalSent)}</span></span>
                        <span class="ps-item">&darr; <span class="ps-value">${formatBytes(totalReceived)}</span></span>
                        <span class="ps-item">External: <span class="ps-value">${externalCalls}</span></span>
                    </div>
                </div>
                <span class="backend-tag">${esc(data.backend)}${data.verifier_backend ? ' | verifier: ' + esc(data.verifier_backend) : ''}</span>
            </div>
            <div class="provenance-bar">
                <div class="provenance-left">
                    <span class="provenance-label">Provenance Seal</span>
                    <code class="provenance-hash">${esc(sealDisplay)}</code>
                    <span class="seal-status" id="seal-status-${responseId}"></span>
                </div>
                <div class="provenance-actions">
                    <button class="seal-verify-btn" onclick="verifySeal('${responseId}', this)">Check Chain</button>
                    <button class="bundle-export-btn" onclick="exportBundle('${responseId}', this)">Export JSON</button>
                    <button class="bundle-export-btn pdf" onclick="exportBundlePdf('${responseId}', this)">Export PDF</button>
                </div>
            </div>
            <div class="self-attestation-notice">
                This seal proves the audit trail was not modified after writing. It does not prove the content is factually correct — consistency checks use the same type of model that generated the response.
            </div>
            ${premiseHtml}
            <div class="response-columns">
                <div class="process-column">
                    <div class="process-column-header">Process — what Glass did</div>
                    <div class="audit-section">
                        <div class="audit-section-label">${data.audit_trail.length} operations</div>
                        ${renderAuditTimeline(data.audit_trail)}
                    </div>
                    <div class="reasoning-section">
                        <div class="reasoning-section-label" onclick="toggleReasoning('${reasoningId}')">Reasoning trace (click to expand)</div>
                        <div class="reasoning-text collapsed" id="${reasoningId}">${esc(data.reasoning_trace) || '(No reasoning trace available)'}</div>
                    </div>
                </div>
                <div class="result-column">
                    <div class="result-column-header">Result — what Glass found</div>
                    <div class="response-body">
                        <div class="response-text">${esc(data.raw_response)}</div>
                    </div>
                    <div class="claims-section">
                        <h3>Claims (${data.claims.length})</h3>
                        ${claimsHtml || '<p style="color: var(--text-muted); font-size: 14px;">No factual claims extracted</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;

    responsesDiv.insertAdjacentHTML('afterbegin', html);

    // Hide example chips after first response
    const chipsEl = document.getElementById('example-chips');
    if (chipsEl) chipsEl.style.display = 'none';
}

function toggleReasoning(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('collapsed');
        const label = el.previousElementSibling;
        if (label) {
            label.textContent = el.classList.contains('collapsed')
                ? 'Reasoning trace (click to expand)'
                : 'Reasoning trace (click to collapse)';
        }
    }
}

function esc(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setPipelineStage(stage) {
    const stages = ['generate', 'decompose', 'verify', 'audit', 'seal'];
    const idx = stages.indexOf(stage);
    stages.forEach((s, i) => {
        const el = document.getElementById('stage-' + s);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (i < idx) el.classList.add('done');
        if (i === idx) el.classList.add('active');
    });
}

function clearPipelineStages() {
    ['generate', 'decompose', 'verify', 'audit', 'seal'].forEach(s => {
        const el = document.getElementById('stage-' + s);
        if (el) el.classList.remove('active', 'done');
    });
}

queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query || !backendAvailable) return;

    queryInput.value = '';
    submitBtn.disabled = true;
    loading.classList.add('visible');

    // Clear previous stage states
    clearPipelineStages();

    // Use SSE streaming endpoint for real pipeline progress.
    // A transparency tool must not simulate its own process —
    // every stage indicator reflects actual server-side completion.
    try {
        const resp = await fetch('/api/query/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            alert(err.detail || 'Query failed');
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();  // keep incomplete line

            let currentEvent = null;
            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.substring(7);
                } else if (line.startsWith('data: ') && currentEvent) {
                    const data = JSON.parse(line.substring(6));

                    if (currentEvent === 'stage') {
                        const stageEl = document.getElementById('stage-' + data.name);
                        if (stageEl) {
                            if (data.status === 'started') {
                                stageEl.classList.add('active');
                                stageEl.classList.remove('done');
                            } else if (data.status === 'done') {
                                stageEl.classList.remove('active');
                                stageEl.classList.add('done');
                            }
                        }
                        // Map decompose+verify done to mark audit stage
                        if (data.name === 'verify' && data.status === 'done') {
                            const auditEl = document.getElementById('stage-audit');
                            if (auditEl) auditEl.classList.add('done');
                        }
                    } else if (currentEvent === 'result') {
                        finalData = data;
                    } else if (currentEvent === 'error') {
                        alert(data.detail || 'Query failed');
                    }
                    currentEvent = null;
                }
            }
        }

        if (finalData) {
            // Mark all stages done
            ['generate', 'decompose', 'verify', 'audit', 'seal'].forEach(s => {
                const el = document.getElementById('stage-' + s);
                if (el) {
                    el.classList.remove('active');
                    el.classList.add('done');
                }
            });
            renderResponse(finalData);
        }
    } catch (err) {
        alert('Request failed: ' + err.message);
    } finally {
        submitBtn.disabled = false;
        loading.classList.remove('visible');
        clearPipelineStages();
    }
});

// Example query chips
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const query = chip.dataset.query;
        if (query && backendAvailable) {
            queryInput.value = query;
            queryForm.dispatchEvent(new Event('submit'));
        }
    });
});

// Hide chips after first query
const chipsDiv = document.getElementById('example-chips');
const originalSubmit = queryForm.onsubmit;

function hideChipsOnFirstResponse() {
    if (chipsDiv && responsesDiv.children.length > 0) {
        chipsDiv.style.display = 'none';
    }
}

// PDF export handler
async function exportBundlePdf(responseId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = 'Generating PDF...';
    try {
        const resp = await fetch(`/api/response/${responseId}/bundle.pdf`);
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `glass-proof-${responseId.substring(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        btnEl.textContent = 'PDF Exported';
        btnEl.className = 'bundle-export-btn exported';
        setTimeout(() => {
            btnEl.textContent = 'Export PDF';
            btnEl.className = 'bundle-export-btn pdf';
            btnEl.disabled = false;
        }, 2000);
    } catch (err) {
        btnEl.textContent = 'Error';
        btnEl.disabled = false;
    }
}

// Init
checkStatus();
