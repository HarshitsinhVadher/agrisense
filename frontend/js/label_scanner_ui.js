/* AI Label Scanner Component (Matches Mobile App.js 1:1) */

let scanProgressTimer = null;

async function handleLabelScanUpload(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('file', file);
  formData.append('lang', getCurrentLanguage());

  renderScanLoading();

  try {
    const res = await fetch('/api/scan-label', {
      method: 'POST',
      headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
      body: formData
    });
    const data = await res.json();
    renderLabelScanResult(data);
  } catch (err) {
    console.error("Label scan error:", err);
    showScanError("Could not upload image or analyze label.");
  } finally {
    clearInterval(scanProgressTimer);
  }
}

async function submitTextLabelScan() {
  const query = (document.getElementById('label-text-input')?.value || '').trim();
  if (!query) {
    showToast("⚠️ Please enter a product name or ingredient.");
    return;
  }

  renderScanLoading();

  try {
    const res = await fetch('/api/scan-label-text', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ query, lang: getCurrentLanguage() })
    });
    const data = await res.json();
    renderLabelScanResult(data);
  } catch (err) {
    console.error("Text scan error:", err);
    showScanError("Could not query chemical database.");
  } finally {
    clearInterval(scanProgressTimer);
  }
}

function renderScanLoading() {
  const resultsContainer = document.getElementById('label-scan-results');
  if (!resultsContainer) return;

  const steps = [
    "📷 Extracting label text & brand...",
    "🧪 Matching chemical database...",
    "🤖 Generating Gemini AI agronomic guide..."
  ];
  let currentStep = 0;

  resultsContainer.innerHTML = `
    <div style="text-align:center; padding:24px; background:#fff; border-radius:14px; margin-top:16px;">
      <div class="spinner"></div>
      <p id="scan-step-msg" style="margin-top:10px; font-size:14px; font-weight:700; color:#1b4332;">
        ${steps[0]}
      </p>
    </div>
  `;

  scanProgressTimer = setInterval(() => {
    currentStep = (currentStep + 1) % steps.length;
    const msgEl = document.getElementById('scan-step-msg');
    if (msgEl) msgEl.textContent = steps[currentStep];
  }, 2000);
}

function showScanError(msg) {
  const container = document.getElementById('label-scan-results');
  if (container) {
    container.innerHTML = `<p style="color:#dc2626; font-size:13px; padding:16px;">⚠️ ${msg}</p>`;
  }
}

function getConfidenceColor(confidence) {
  const score = parseFloat(confidence) || 0;
  if (score >= 80) return '#10b981'; // Green
  if (score >= 50) return '#f59e0b'; // Amber
  return '#6b7280'; // Gray
}

function renderLabelScanResult(data) {
  const container = document.getElementById('label-scan-results');
  if (!container) return;

  const product = data.matched_product;

  if (product) {
    const confidence = data.match_confidence || 90;
    const confColor = getConfidenceColor(confidence);
    const pests = Array.isArray(product.target_pests) ? product.target_pests.join(', ') : (product.target_pests || 'N/A');

    container.innerHTML = `
      <div class="card" style="margin-top:16px; border:2px solid #d1fae5; background:#fff;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <h3 style="font-size:18px; font-weight:800; color:#1b4332; margin:0;">
            📦 ${product.name}
          </h3>
          <span style="background:${confColor}; color:#fff; font-size:11px; font-weight:700; padding:4px 10px; border-radius:12px;">
            ${confidence}% Match
          </span>
        </div>

        <div style="margin-bottom:8px;">
          <label style="font-size:11px; color:#6b7280; margin:0;">${t('brand')}:</label>
          <div style="font-size:14px; font-weight:700; color:#1f2937;">${product.brand || 'N/A'}</div>
        </div>

        <div style="margin-bottom:8px;">
          <label style="font-size:11px; color:#6b7280; margin:0;">${t('active')}:</label>
          <div style="font-size:14px; font-weight:700; color:#2563eb;">${product.active_ingredient || 'N/A'}</div>
        </div>

        <div style="margin-bottom:8px;">
          <label style="font-size:11px; color:#6b7280; margin:0;">${t('dosage')}:</label>
          <div style="font-size:13px; font-weight:600; color:#166534; background:#f0fdf4; padding:8px 10px; border-radius:6px;">
            ${product.recommended_dosage || 'Follow label instructions.'}
          </div>
        </div>

        <div style="margin-bottom:8px;">
          <label style="font-size:11px; color:#6b7280; margin:0;">🎯 ${t('target_pests')}:</label>
          <div style="font-size:13px; color:#374151;">${pests}</div>
        </div>

        <div style="margin-top:10px;">
          <label style="font-size:11px; color:#6b7280; margin:0;">⚠️ ${t('safety')}:</label>
          <div style="font-size:12px; color:#991b1b; background:#fef2f2; padding:8px 10px; border-radius:6px;">
            ${product.safety_precaution || 'Wear gloves and mask. Keep away from children.'}
          </div>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="card" style="margin-top:16px; background:#fff;">
        <h4 style="font-size:15px; font-weight:700; color:#1b4332; margin-bottom:8px;">🔍 Product Identification Result</h4>
        <p style="font-size:13px; color:#374151; line-height:1.5;">${data.ai_summary || 'No matching product found.'}</p>
        ${data.disclaimer ? `<p style="font-size:11px; color:#dc2626; margin-top:8px;">⚠️ ${data.disclaimer}</p>` : ''}
      </div>
    `;
  }
}
