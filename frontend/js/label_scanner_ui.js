/* Seed & Product Label Scanner UI Component */

async function handleLabelScanUpload(fileInput) {
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('lang', getCurrentLanguage());

  renderLabelScanLoading();

  try {
    const res = await fetch('/api/scan-label', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    renderLabelScanResults(data);
    showToast("🔍 Product label scanned and analyzed!");
  } catch (err) {
    console.error("Label scan error:", err);
    showToast("⚠️ Label analysis failed.");
  }
}

async function submitTextLabelScan() {
  const text = document.getElementById('label-text-input')?.value;
  if (!text || text.trim() === '') {
    showToast("Please enter product name or label text.");
    return;
  }

  const formData = new FormData();
  formData.append('text_input', text);
  formData.append('lang', getCurrentLanguage());

  renderLabelScanLoading();

  try {
    const res = await fetch('/api/scan-label', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    renderLabelScanResults(data);
  } catch (err) {
    showToast("⚠️ Label search failed.");
  }
}

function renderLabelScanLoading() {
  const container = document.getElementById('label-scan-results');
  if (container) {
    container.innerHTML = `<div style="text-align:center; padding:20px;"><div class="spinner"></div><p style="margin-top:8px; font-size:13px; color:#1b4332;">Scanning label OCR & querying database...</p></div>`;
  }
}

function renderLabelScanResults(data) {
  const container = document.getElementById('label-scan-results');
  if (!container) return;

  const prod = data.matched_product || {};

  container.innerHTML = `
    <div class="result-crop-card rank-1" style="margin-top:10px;">
      <div class="crop-header">
        <div class="crop-name">🏷️ ${prod.name || 'Unknown Product'}</div>
        <div class="confidence-badge">${data.match_confidence}% DB Match</div>
      </div>
      <p style="font-size:12px; color:#4b5563; margin-bottom:10px;">Brand: <strong>${prod.brand || 'Generic'}</strong> | Type: <strong>${prod.type || 'Agri-Input'}</strong></p>

      <div style="font-size:13px; line-height:1.6; margin-bottom:12px;">
        <p>🧪 <strong>${t('active_ing')}:</strong> ${prod.active_ingredient || 'N/A'}</p>
        <p>🐛 <strong>${t('target_pests')}:</strong> ${Array.isArray(prod.target_pests) ? prod.target_pests.join(', ') : 'N/A'}</p>
        <p>🌱 <strong>${t('suitable_crops')}:</strong> ${Array.isArray(prod.suitable_crops) ? prod.suitable_crops.join(', ') : 'N/A'}</p>
        <p style="background:#eef7f2; padding:6px 10px; border-radius:6px; margin-top:6px;">💧 <strong>${t('dosage')}:</strong> ${prod.dosage || 'Follow package instructions'}</p>
      </div>

      <div class="ai-summary-box">
        <h4>${t('ai_summary_title')}</h4>
        <div style="white-space: pre-line;">${data.ai_summary}</div>
      </div>

      <div class="advisory-card warning" style="margin-top:14px;">
        <div class="advisory-msg">${data.disclaimer || t('safety_disclaimer')}</div>
      </div>
    </div>
  `;
}
