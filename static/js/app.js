/**
 * NexusRisk AI — Transaction Risk Investigation Assistant Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  let selectedCustomerId = 'CUST-1002'; // Default to anomalous customer
  let customTransactionsData = null;
  let currentAnalysisData = null;

  // DOM Element References
  const presetButtons = document.querySelectorAll('.preset-btn');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const browseBtn = document.getElementById('browse-btn');
  const analyzeBtn = document.getElementById('analyze-btn');
  const loadingSpinner = document.getElementById('loading-spinner');
  const dashboard = document.getElementById('investigation-dashboard');

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

  const ledgerTbody = document.getElementById('ledger-tbody');
  const ledgerCountMeta = document.getElementById('ledger-count-meta');
  const filterBtns = document.querySelectorAll('.filter-btn');

  // 1. Customer Preset Button Event Handlers
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedCustomerId = btn.getAttribute('data-cid');
      customTransactionsData = null; // reset custom upload
      runAnalysis();
    });
  });

  // 2. Drag & Drop File Upload Handlers
  browseBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFileUpload(file);
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#58a6ff';
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = '#30363d';
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.style.borderColor = '#30363d';
    if (e.dataTransfer.files.length) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  function handleFileUpload(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target.result);
        customTransactionsData = Array.isArray(parsed) ? parsed : (parsed.transactions || []);
        selectedCustomerId = parsed.customer_id || 'CUSTOM-UPLOAD';
        
        // Unselect preset buttons
        presetButtons.forEach(b => b.classList.remove('active'));
        alert(`Loaded ${customTransactionsData.length} transactions from uploaded JSON!`);
        runAnalysis();
      } catch (err) {
        alert('Invalid JSON file format. Please upload a valid customer transaction history JSON.');
      }
    };
    reader.readAsText(file);
  }

  // 3. Run Analysis Button
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

      if (!response.ok) {
        throw new Error(`API returned HTTP ${response.status}`);
      }

      const data = await response.json();
      currentAnalysisData = data;

      // Also fetch raw customer info if using sample customer
      let rawCustomer = null;
      if (!customTransactionsData) {
        const cRes = await fetch(`/api/customers/${selectedCustomerId}`);
        if (cRes.ok) rawCustomer = await cRes.json();
      }

      renderDashboard(data, rawCustomer);
    } catch (err) {
      console.error('Analysis failed:', err);
      alert('Failed to analyze transaction history: ' + err.message);
    } finally {
      loadingSpinner.classList.add('hidden');
    }
  }

  // 4. Render Dashboard Components
  function renderDashboard(data, rawCustomer) {
    const attentionNeeded = data.attention_needed;

    // Headline Status Banner
    attentionStatusEl.innerHTML = attentionNeeded
      ? `<div class="status-box yes">⚠️ ATTENTION NEEDED: YES</div>`
      : `<div class="status-box no">✅ ATTENTION NEEDED: NO</div>`;

    const cName = rawCustomer ? rawCustomer.customer_name : 'Customer ' + data.customer_id;
    const cType = rawCustomer ? rawCustomer.account_type : 'Standard Account';
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

    // Triggered Rules
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
          <div class="rule-txs">Flagged IDs: ${r.flagged_transaction_ids.map(id => `<code>${id}</code>`).join(', ')}</div>
        </div>
      `).join('');
    }

    // Baseline Stats
    const stats = data.summary_stats || {};
    baselineStatsContainer.innerHTML = `
      <div class="stat-box">
        <span class="stat-lbl">TOTAL EVALUATED</span>
        <span class="stat-val">${stats.total_transactions || 0} txns</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">HISTORICAL AVG</span>
        <span class="stat-val">USD ${(stats.avg_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">90TH PERCENTILE</span>
        <span class="stat-val">USD ${(stats.p90_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
      </div>
      <div class="stat-box">
        <span class="stat-lbl">KNOWN PAYEES</span>
        <span class="stat-val">${stats.known_payees_count || 0} payees</span>
      </div>
    `;

    // Narrative Report Body (Simple markdown to HTML renderer)
    reportSourceTag.textContent = `Source: ${data.report_source === 'gemini_llm' ? 'Gemini 2.5 Flash' : 'Deterministic Rule Engine Fallback'}`;
    narrativeReportBody.innerHTML = formatMarkdown(data.narrative_report);

    // Transaction Ledger
    const allTxs = rawCustomer ? rawCustomer.transactions : (customTransactionsData || []);
    const flaggedSet = new Set(data.flagged_transaction_ids || []);
    renderLedger(allTxs, flaggedSet, 'all');
  }

  // 5. Render Transaction Table
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
        <tr class="${isFlagged ? 'flagged-row' : ''}">
          <td style="font-family: var(--font-mono); font-weight: 600;">${t.transaction_id}</td>
          <td>${formatDate(t.timestamp)}</td>
          <td>${t.description || 'N/A'}</td>
          <td><strong>${t.payee || 'N/A'}</strong></td>
          <td><span style="font-size: 11px; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${t.channel || 'N/A'}</span></td>
          <td class="text-right" style="font-family: var(--font-mono); font-weight: 600;">USD ${(t.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
          <td>${isFlagged ? '<span class="badge badge-high">⚠️ Flagged</span>' : '<span style="color: var(--text-muted); font-size: 11px;">Normal</span>'}</td>
        </tr>
      `;
    }).join('');
  }

  // Filter Buttons Handler
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filterMode = btn.getAttribute('data-filter');
      if (currentAnalysisData) {
        const flaggedSet = new Set(currentAnalysisData.flagged_transaction_ids || []);
        // Fetch current txs
        fetch(`/api/customers/${selectedCustomerId}`)
          .then(r => r.json())
          .then(cData => renderLedger(cData.transactions || [], flaggedSet, filterMode))
          .catch(() => renderLedger(customTransactionsData || [], flaggedSet, filterMode));
      }
    });
  });

  // Copy Report Button
  copyReportBtn.addEventListener('click', () => {
    if (currentAnalysisData && currentAnalysisData.narrative_report) {
      navigator.clipboard.writeText(currentAnalysisData.narrative_report);
      copyReportBtn.textContent = '✅ Copied!';
      setTimeout(() => copyReportBtn.textContent = '📋 Copy Report', 2000);
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
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/^1\. (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/g, '<br><br>');
    return html;
  }

  function formatDate(ts) {
    if (!ts) return '';
    try {
      const dt = new Date(ts);
      return dt.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return ts;
    }
  }

  // Initial Load: Analyze default customer (CUST-1002)
  runAnalysis();
});
