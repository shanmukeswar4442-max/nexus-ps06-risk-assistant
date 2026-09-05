/**
 * NexusRisk AI — Interactive SPA Frontend Application Logic
 * Supports: Customer Dashboard with Status Chips, Report Download, Clickable Citation Highlighting, Settings Session Keys, Upload (CSV/JSON), and Real-Time Transactions.
 */

document.addEventListener('DOMContentLoaded', () => {
  let selectedCustomerId = 'CUST-1002'; // Default to anomalous customer
  let customTransactionsData = null;
  let currentAnalysisData = null;
  let customerListCache = [];

  // DOM Elements
  const customerPresetContainer = document.getElementById('customer-preset-buttons');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const browseBtn = document.getElementById('browse-btn');
  const analyzeBtn = document.getElementById('analyze-btn');
  const loadingSpinner = document.getElementById('loading-spinner');
  const dashboard = document.getElementById('investigation-dashboard');

  const addTxnForm = document.getElementById('add-txn-form');
  const txnTimeInput = document.getElementById('txn-time');
  const txnPayeeInput = document.getElementById('txn-payee');
  const txnDescInput = document.getElementById('txn-desc');
  const txnAmountInput = document.getElementById('txn-amount');
  const txnChannelSelect = document.getElementById('txn-channel');
  const txnCategorySelect = document.getElementById('txn-category');

  const attentionStatusEl = document.getElementById('attention-status');
  const customerMetaEl = document.getElementById('customer-meta-display');
  const riskScoreValEl = document.getElementById('risk-score-val');
  const confidenceValEl = document.getElementById('confidence-val');

  const triggeredRulesContainer = document.getElementById('triggered-rules-container');
  const ruleCountTag = document.getElementById('rule-count-tag');
  const baselineStatsContainer = document.getElementById('baseline-stats-container');
  const narrativeReportBody = document.getElementById('narrative-report-body');
  const reportSourceTag = document.getElementById('report-source-tag');
  const copyReportBtn = document.getElementById('copy-report-btn');
  const downloadReportBtn = document.getElementById('download-report-btn');

  const ledgerTbody = document.getElementById('ledger-tbody');
  const ledgerCountMeta = document.getElementById('ledger-count-meta');
  const filterBtns = document.querySelectorAll('.filter-btn');

  // Settings Modal Elements
  const openSettingsBtn = document.getElementById('open-settings-btn');
  const closeSettingsBtn = document.getElementById('close-settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const sessionKeyInput = document.getElementById('session-key-input');
  const toggleKeyVisBtn = document.getElementById('toggle-key-vis');
  const saveKeyBtn = document.getElementById('save-key-btn');
  const clearKeyBtn = document.getElementById('clear-key-btn');
  const modalKeyStatus = document.getElementById('modal-key-status');
  const headerKeyStatus = document.getElementById('header-key-status');

  // Set default datetime input to now
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  txnTimeInput.value = now.toISOString().slice(0, 16);

  // Initialize
  fetchCustomerList();
  checkApiKeyStatus();

  // 1. Fetch & Render Customer List with Status Chips
  async function fetchCustomerList() {
    try {
      const res = await fetch('/api/customers');
      if (res.ok) {
        const data = await res.json();
        customerListCache = data.customers || [];
        renderCustomerPresets();
      }
    } catch (e) {
      console.error('Failed to fetch customers:', e);
    }
  }

  function renderCustomerPresets() {
    if (!customerPresetContainer) return;
    
    customerPresetContainer.innerHTML = customerListCache.map(c => {
      const isActive = c.customer_id === selectedCustomerId && !customTransactionsData;
      let chipHtml = '';
      if (c.status_chip === 'Needs Attention') {
        chipHtml = `<span class="chip chip-attention">Needs Attention</span>`;
      } else if (c.status_chip === 'Clean') {
        chipHtml = `<span class="chip chip-clean">Clean</span>`;
      } else {
        chipHtml = `<span class="chip chip-not-analyzed">Not Analyzed</span>`;
      }

      return `
        <button class="preset-btn ${isActive ? 'active' : ''}" data-cid="${c.customer_id}">
          <div class="btn-top">
            <span class="c-name">${c.customer_name}</span>
            ${chipHtml}
          </div>
          <div class="btn-sub">${c.customer_id} • ${c.total_transactions} txns (${c.risk_profile})</div>
        </button>
      `;
    }).join('');

    // Re-attach event listeners
    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedCustomerId = btn.getAttribute('data-cid');
        customTransactionsData = null;
        renderCustomerPresets();
        runAnalysis();
      });
    });
  }

  // 2. Settings Modal Event Handlers
  openSettingsBtn.addEventListener('click', () => {
    settingsModal.classList.remove('hidden');
    checkApiKeyStatus();
  });

  closeSettingsBtn.addEventListener('click', () => settingsModal.classList.add('hidden'));

  toggleKeyVisBtn.addEventListener('click', () => {
    sessionKeyInput.type = sessionKeyInput.type === 'password' ? 'text' : 'password';
  });

  saveKeyBtn.addEventListener('click', async () => {
    const key = sessionKeyInput.value.trim();
    if (!key) return;
    try {
      const res = await fetch('/api/settings/set-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key })
      });
      if (res.ok) {
        alert('Runtime API key saved for this session!');
        sessionKeyInput.value = '';
        checkApiKeyStatus();
        settingsModal.classList.add('hidden');
      }
    } catch (e) {
      alert('Failed to set API key');
    }
  });

  clearKeyBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/settings/set-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: '' })
      });
      sessionKeyInput.value = '';
      checkApiKeyStatus();
      alert('Session API key cleared!');
    } catch (e) {
      console.error(e);
    }
  });

  async function checkApiKeyStatus() {
    try {
      const res = await fetch('/api/settings/key-status');
      if (res.ok) {
        const data = await res.json();
        if (data.active) {
          const srcText = data.source === 'session' ? 'Session Override' : 'Environment Variable';
          headerKeyStatus.textContent = `🟢 Key Active (${srcText})`;
          modalKeyStatus.innerHTML = `<strong style="color: var(--accent-green)">🟢 Active</strong> — Key source: ${srcText}`;
        } else {
          headerKeyStatus.textContent = `⚪ No Key (Rule Fallback)`;
          modalKeyStatus.innerHTML = `<strong style="color: var(--text-muted)">⚪ Inactive</strong> — No key configured. System uses deterministic rule fallback.`;
        }
      }
    } catch (e) {
      headerKeyStatus.textContent = `⚪ Key Status Unknown`;
    }
  }

  // 3. Real-Time Add Transaction Form Handler
  addTxnForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const newTxn = {
      transaction_id: `TXN-LIVE-${Date.now().toString().slice(-5)}`,
      customer_id: selectedCustomerId,
      timestamp: new Date(txnTimeInput.value).toISOString(),
      description: txnDescInput.value.trim(),
      payee: txnPayeeInput.value.trim(),
      amount: parseFloat(txnAmountInput.value),
      channel: txnChannelSelect.value,
      category: txnCategorySelect.value,
      status: "Completed"
    };

    if (!customTransactionsData) {
      try {
        const res = await fetch(`/api/customers/${selectedCustomerId}`);
        if (res.ok) {
          const cData = await res.json();
          customTransactionsData = cData.transactions || [];
        } else {
          customTransactionsData = [];
        }
      } catch (err) {
        customTransactionsData = [];
      }
    }

    customTransactionsData.push(newTxn);
    txnPayeeInput.value = '';
    txnDescInput.value = '';
    txnAmountInput.value = '';

    alert(`Live transaction [${newTxn.transaction_id}] added! Running real-time risk investigation...`);
    runAnalysis();
  });

  // 4. File Upload (CSV/JSON) Handler
  browseBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFileUpload(e.target.files[0]);
  });

  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.style.borderColor = '#58a6ff'; });
  dropzone.addEventListener('dragleave', () => { dropzone.style.borderColor = '#30363d'; });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#30363d';
    if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
  });

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    loadingSpinner.classList.remove('hidden');
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }
      const data = await res.json();
      selectedCustomerId = data.customer_id;
      currentAnalysisData = data.analysis_result;
      customTransactionsData = null;

      alert(`Uploaded & analyzed ${data.total_parsed} transactions for customer ${data.customer_id}!`);
      fetchCustomerList();
      renderDashboard(currentAnalysisData, null);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      loadingSpinner.classList.add('hidden');
    }
  }

  // 5. Run Analysis Engine
  analyzeBtn.addEventListener('click', () => runAnalysis());

  async function runAnalysis() {
    loadingSpinner.classList.remove('hidden');
    try {
      let payload = {};
      if (customTransactionsData) {
        payload = { customer_id: selectedCustomerId, transactions: customTransactionsData };
      } else {
        payload = { customer_id: selectedCustomerId, transactions: [] };
      }

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error(`API returned HTTP ${response.status}`);

      const data = await response.json();
      currentAnalysisData = data;

      let rawCustomer = null;
      if (!customTransactionsData) {
        const cRes = await fetch(`/api/customers/${selectedCustomerId}`);
        if (cRes.ok) rawCustomer = await cRes.json();
      }

      fetchCustomerList();
      renderDashboard(data, rawCustomer);
    } catch (err) {
      console.error('Analysis failed:', err);
      alert('Failed to analyze transaction history: ' + err.message);
    } finally {
      loadingSpinner.classList.add('hidden');
    }
  }

  // 6. Render Dashboard Components
  function renderDashboard(data, rawCustomer) {
    const attentionNeeded = data.attention_needed;

    attentionStatusEl.innerHTML = attentionNeeded
      ? `<div class="status-box yes">⚠️ ATTENTION NEEDED: YES</div>`
      : `<div class="status-box no">✅ ATTENTION NEEDED: NO</div>`;

    const cName = rawCustomer ? rawCustomer.customer_name : 'Customer ' + data.customer_id;
    const cType = rawCustomer ? rawCustomer.account_type : 'Uploaded Dataset';
    customerMetaEl.innerHTML = `Customer ID: <strong>${data.customer_id}</strong> (${cName}) • <span>${cType}</span>`;

    riskScoreValEl.textContent = data.overall_risk_score;
    confidenceValEl.textContent = data.confidence_level;

    if (data.overall_risk_score >= 60) {
      riskScoreValEl.style.color = '#f85149';
    } else if (data.overall_risk_score >= 30) {
      riskScoreValEl.style.color = '#d29922';
    } else {
      riskScoreValEl.style.color = '#2ea043';
    }

    // Triggered Rules with Clickable Citation Badges
    const rules = data.triggered_rules || [];
    ruleCountTag.textContent = `${rules.length} Rule${rules.length === 1 ? '' : 's'} Triggered`;

    if (rules.length === 0) {
      triggeredRulesContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 13px; padding: 12px 0;">No deterministic risk rules triggered. Customer activity matches baseline behavior.</p>`;
    } else {
      triggeredRulesContainer.innerHTML = rules.map(r => `
        <div class="rule-item">
          <div class="rule-header">
            <span class="rule-title">${r.rule_name}</span>
            <span class="badge ${r.severity === 'HIGH' ? 'badge-high' : 'badge-borderline'}">${r.severity}</span>
          </div>
          <p class="rule-desc">${r.description}</p>
          <div class="rule-txs">Flagged IDs: ${r.flagged_transaction_ids.map(id => `<code class="citation-tag" data-txid="${id}">${id}</code>`).join(', ')}</div>
        </div>
      `).join('');
    }

    // Baseline Stats (INR ₹)
    const stats = data.summary_stats || {};
    baselineStatsContainer.innerHTML = `
      <div class="stat-box">
        <span class="stat-lbl">TOTAL EVALUATED</span>
        <span class="stat-val">${stats.total_transactions || 0} txns</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">HISTORICAL AVG</span>
        <span class="stat-val">₹${(stats.avg_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">90TH PERCENTILE</span>
        <span class="stat-val">₹${(stats.p90_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">KNOWN PAYEES</span>
        <span class="stat-val">${stats.known_payees_count || 0} payees</span>
      </div>
    `;

    // Narrative Report Body
    reportSourceTag.textContent = `Source: ${data.report_source === 'gemini_llm' ? 'Gemini 2.5 Flash' : 'Deterministic Rule Engine Fallback'}`;
    narrativeReportBody.innerHTML = formatMarkdown(data.narrative_report);

    // Transaction Ledger
    const allTxs = customTransactionsData ? customTransactionsData : (rawCustomer ? rawCustomer.transactions : []);
    const flaggedSet = new Set(data.flagged_transaction_ids || []);
    renderLedger(allTxs, flaggedSet, 'all');

    // Attach Click Event to Citations for Instant Highlighting
    document.querySelectorAll('.citation-tag').forEach(tag => {
      tag.addEventListener('click', () => {
        const txid = tag.getAttribute('data-txid');
        highlightTransactionRow(txid);
      });
    });
  }

  // 7. Render Transaction Table
  function renderLedger(txs, flaggedSet, filterMode) {
    const displayTxs = filterMode === 'flagged' ? txs.filter(t => flaggedSet.has(t.transaction_id)) : txs;
    ledgerCountMeta.textContent = `Showing ${displayTxs.length} of ${txs.length} total transactions`;

    if (displayTxs.length === 0) {
      ledgerTbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">No transactions matching filter.</td></tr>`;
      return;
    }

    ledgerTbody.innerHTML = displayTxs.map(t => {
      const isFlagged = flaggedSet.has(t.transaction_id);
      return `
        <tr id="row-${t.transaction_id}" class="${isFlagged ? 'flagged-row' : ''}">
          <td style="font-family: var(--font-mono); font-weight: 600;">${t.transaction_id}</td>
          <td>${formatDate(t.timestamp)}</td>
          <td>${t.description || 'N/A'}</td>
          <td><strong>${t.payee || 'N/A'}</strong></td>
          <td><span style="font-size: 11px; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${t.channel || 'N/A'}</span></td>
          <td class="text-right" style="font-family: var(--font-mono); font-weight: 600;">₹${(t.amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
          <td>${isFlagged ? '<span class="badge badge-high">⚠️ Flagged</span>' : '<span style="color: var(--text-muted); font-size: 11px;">Normal</span>'}</td>
        </tr>
      `;
    }).join('');
  }

  function highlightTransactionRow(txid) {
    document.querySelectorAll('.ledger-table tr').forEach(r => r.classList.remove('highlighted-row'));
    const targetRow = document.getElementById(`row-${txid}`);
    if (targetRow) {
      targetRow.classList.add('highlighted-row');
      targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // Download Report (.md)
  downloadReportBtn.addEventListener('click', async () => {
    if (!currentAnalysisData || !currentAnalysisData.narrative_report) return;
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_id: selectedCustomerId,
          report_content: currentAnalysisData.narrative_report,
          format: 'markdown'
        })
      });
      if (res.ok) {
        const text = await res.text();
        const blob = new Blob([text], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Investigation_Report_${selectedCustomerId}.md`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      alert('Failed to download report');
    }
  });

  // Copy Report Button
  copyReportBtn.addEventListener('click', () => {
    if (currentAnalysisData && currentAnalysisData.narrative_report) {
      navigator.clipboard.writeText(currentAnalysisData.narrative_report);
      copyReportBtn.textContent = '✅ Copied!';
      setTimeout(() => copyReportBtn.textContent = '📋 Copy', 2000);
    }
  });

  // Simple Markdown Formatter
  function formatMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
      .replace(/^\*\*([^*]+)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*\*([^*]+)\*\*/gim, '<strong>$1</strong>')
      .replace(/`([^`]+)`/gim, '<code class="citation-tag" data-txid="$1">$1</code>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/^1\. (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/g, '<br><br>');
    return html;
  }

  function formatDate(ts) {
    if (!ts) return '';
    try {
      const dt = new Date(ts);
      return dt.toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return ts;
    }
  }

  // Initial Load
  runAnalysis();
});
