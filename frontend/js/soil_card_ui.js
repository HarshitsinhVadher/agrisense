/* Soil Health Card UI Component */
let currentParsedSoilData = null;

async function handleSoilCardUpload(fileInput) {
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  renderSoilCardLoading();

  try {
    const res = await fetch('/api/parse-soil-card', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    currentParsedSoilData = data;
    renderSoilCardTable(data);
    showToast("✅ Soil Health Card scanned successfully!");
  } catch (err) {
    console.error("Soil card upload error:", err);
    showToast("⚠️ OCR processing failed.");
  }
}

async function useSampleSoilCard() {
  renderSoilCardLoading();
  try {
    const res = await fetch('/api/parse-soil-card', {
      method: 'POST'
    });
    const data = await res.json();
    currentParsedSoilData = data;
    renderSoilCardTable(data);
    showToast("📄 Loaded sample Gujarat Soil Health Card!");
  } catch (err) {
    showToast("⚠️ Failed to load sample soil card.");
  }
}

function renderSoilCardLoading() {
  const container = document.getElementById('soil-card-results');
  if (container) {
    container.innerHTML = `<div style="text-align:center; padding:20px;"><div class="spinner"></div><p style="margin-top:8px; font-size:13px; color:#1b4332;">Extracting OCR soil parameters...</p></div>`;
  }
}

function renderSoilCardTable(data) {
  const container = document.getElementById('soil-card-results');
  if (!container) return;

  const params = data.parameters || {};
  const confidence = data.confidence || {};
  const status = data.soil_status || {};

  container.innerHTML = `
    <h3 class="card-title">${t('extracted_params')}</h3>
    <table class="soil-table">
      <thead>
        <tr>
          <th>${t('param')}</th>
          <th>${t('value')}</th>
          <th>${t('status')}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Available Nitrogen (N)</td>
          <td><input type="number" id="edit-N" value="${params.N || 180}" style="width:70px; padding:3px 6px;"> kg/ha</td>
          <td><span class="status-badge ${getBadgeClass(status.Nitrogen)}">${status.Nitrogen || 'Medium'}</span></td>
        </tr>
        <tr>
          <td>Available Phosphorus (P)</td>
          <td><input type="number" id="edit-P" value="${params.P || 42}" style="width:70px; padding:3px 6px;"> kg/ha</td>
          <td><span class="status-badge ${getBadgeClass(status.Phosphorus)}">${status.Phosphorus || 'Medium'}</span></td>
        </tr>
        <tr>
          <td>Available Potassium (K)</td>
          <td><input type="number" id="edit-K" value="${params.K || 160}" style="width:70px; padding:3px 6px;"> kg/ha</td>
          <td><span class="status-badge ${getBadgeClass(status.Potassium)}">${status.Potassium || 'Medium'}</span></td>
        </tr>
        <tr>
          <td>Soil pH</td>
          <td><input type="number" step="0.1" id="edit-pH" value="${params.pH || 7.2}" style="width:70px; padding:3px 6px;"></td>
          <td><span class="status-badge ${params.pH < 6.5 ? 'low' : (params.pH > 7.5 ? 'high' : 'medium')}">${status.pH_reaction || 'Neutral'}</span></td>
        </tr>
        <tr>
          <td>Electrical Cond. (EC)</td>
          <td>${params.EC || 0.65} dSm-1</td>
          <td>Normal</td>
        </tr>
        <tr>
          <td>Organic Carbon (OC)</td>
          <td>${params.OC || 0.52} %</td>
          <td>Medium</td>
        </tr>
        <tr>
          <td>Zinc (Zn)</td>
          <td>${params.Zn || 0.85} ppm</td>
          <td>Sufficient</td>
        </tr>
        <tr>
          <td>Iron (Fe)</td>
          <td>${params.Fe || 4.2} ppm</td>
          <td>Sufficient</td>
        </tr>
      </tbody>
    </table>

    <button class="btn" onclick="saveSoilCardToProfile()">${t('save_to_profile')}</button>
  `;
}

function getBadgeClass(val) {
  if (!val) return 'medium';
  const l = val.toLowerCase();
  if (l.includes('low')) return 'low';
  if (l.includes('high')) return 'high';
  return 'medium';
}

async function saveSoilCardToProfile() {
  const nVal = parseFloat(document.getElementById('edit-N')?.value || 180);
  const pVal = parseFloat(document.getElementById('edit-P')?.value || 42);
  const kVal = parseFloat(document.getElementById('edit-K')?.value || 160);
  const phVal = parseFloat(document.getElementById('edit-pH')?.value || 7.2);

  try {
    const currRes = await fetch('/api/profile');
    const profile = await currRes.json();

    profile.N = nVal;
    profile.P = pVal;
    profile.K = kVal;
    profile.pH = phVal;

    await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });

    showToast("💾 Saved soil data to Farmer Profile!");
  } catch (err) {
    showToast("⚠️ Could not update profile.");
  }
}
