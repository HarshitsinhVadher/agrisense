/* Crop AI Recommendation Component (Matches Mobile App.js 1:1) */

window.selectedSoilType = 'Auto-Detect';
window.currentZoneInfo = null;

function setSoilType(soilId) {
  window.selectedSoilType = soilId;
  document.querySelectorAll('.soil-pill').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-soil') === soilId);
  });
}

async function fetchLocationSoilData(lat, lon, locName) {
  const badge = document.getElementById('zone-info-badge');
  try {
    const res = await fetch(`/api/location-soil-data?lat=${lat}&lon=${lon}&location_name=${encodeURIComponent(locName || '')}`);
    const data = await res.json();

    if (data && data.typical_npk) {
      const npk = data.typical_npk;
      if (window.selectedSoilType === 'Auto-Detect') {
        if (npk.N) { document.getElementById('input-N').value = npk.N; syncSlider('input-N', 'val-N'); }
        if (npk.P) { document.getElementById('input-P').value = npk.P; syncSlider('input-P', 'val-P'); }
        if (npk.K) { document.getElementById('input-K').value = npk.K; syncSlider('input-K', 'val-K'); }
        if (npk.pH) { document.getElementById('input-ph').value = npk.pH; syncSlider('input-ph', 'val-ph'); }
      }

      window.currentZoneInfo = data;
      if (badge) {
        badge.style.display = 'block';
        badge.innerHTML = `
          <div style="font-size:12px; color:#065f46; font-weight:700;">
            📍 ${t('gu' === getCurrentLanguage() ? `${data.district} જિલ્લાના ઝોન ડેટા પરથી સ્વચાલિત મેળવેલ` : `${data.district} District Zone Baseline`)}
          </div>
          <div style="font-size:11px; color:#047857; margin-top:2px;">
            Zone: ${data.zone || 'Local'} | Soil: ${data.soil_type || 'Loamy'}
          </div>
        `;
      }
    }
  } catch (e) {
    console.log("Location soil fetch error:", e);
  }
}

function autofillFromWeather() {
  if (window.currentWeatherData && window.currentWeatherData.current) {
    const curr = window.currentWeatherData.current;
    document.getElementById('input-temp').value = Math.round(curr.temperature || 26);
    document.getElementById('input-humidity').value = Math.round(curr.humidity || 75);
    if (curr.rainfall !== undefined) document.getElementById('input-rain').value = Math.round(curr.rainfall);

    syncSlider('input-temp', 'val-temp');
    syncSlider('input-humidity', 'val-humidity');
    syncSlider('input-rain', 'val-rain');

    showToast("🌤️ Temperature, Humidity & Rainfall auto-filled from Weather!");
  } else {
    showToast("⚠️ Weather data not loaded yet.");
  }
}

async function submitCropRecommendation(e) {
  if (e) e.preventDefault();

  const N = parseFloat(document.getElementById('input-N').value) || 0;
  const P = parseFloat(document.getElementById('input-P').value) || 0;
  const K = parseFloat(document.getElementById('input-K').value) || 0;
  const ph = parseFloat(document.getElementById('input-ph').value) || 6.5;
  const temperature = parseFloat(document.getElementById('input-temp').value) || 26;
  const humidity = parseFloat(document.getElementById('input-humidity').value) || 75;
  const rainfall = parseFloat(document.getElementById('input-rain').value) || 110;

  const resultsContainer = document.getElementById('recommend-results');
  resultsContainer.innerHTML = `
    <div style="text-align:center; padding:24px; background:#fff; border-radius:14px; margin-top:16px;">
      <div class="spinner"></div>
      <p style="margin-top:10px; font-size:14px; font-weight:700; color:#1b4332;">
        Running 4-Layer Context Fusion Model...
      </p>
      <p style="font-size:12px; color:#6b7280; margin-top:4px;">
        Location + Soil Texture + NPK Deficits + Gemini Geographical AI
      </p>
    </div>
  `;

  try {
    const lang = typeof getCurrentLanguage === 'function' ? getCurrentLanguage() : 'gu';
    const res = await fetch('/api/recommend-crop', {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        N, P, K, ph, temperature, humidity, rainfall,
        soil_type: window.selectedSoilType,
        location_name: window.currentLocationName || "Anand, Gujarat",
        latitude: window.currentLat || 22.57,
        longitude: window.currentLon || 72.93,
        lang: lang
      })
    });
    const data = await res.json();

    const plan = data.ai_agronomic_plan || {};
    const crops = plan.recommended_crops || data.recommendations || [];

    if (crops.length > 0) {
      resultsContainer.innerHTML = `
        <!-- AI Plan Banner -->
        <div style="background: linear-gradient(135deg, #6d28d9, #4c1d95); color: white; padding: 16px; border-radius: 16px; margin-top: 16px; box-shadow: 0 4px 12px rgba(109,40,217,0.25);">
          <h3 style="font-size: 16px; font-weight: 800; margin-bottom: 4px;">${t('ai_plan_title')}</h3>
          <p style="font-size: 12px; color: #ddd6fe;">
            Zone: ${plan.agro_climatic_zone || 'Middle Gujarat Zone'} | Soil: ${plan.detected_soil_type || window.selectedSoilType}
          </p>
        </div>

        <h4 style="font-size: 15px; font-weight: 700; color: #1b4332; margin-top: 16px; margin-bottom: 12px;">
          ${t('rec_crops_title')}
        </h4>

        ${crops.map((crop, i) => {
          const matchScore = crop.suitability_score || crop.confidence || 90;
          return `
            <div class="result-crop-card ${i === 0 ? 'rank-1' : ''}" style="margin-bottom:12px;">
              <div class="crop-header" style="display:flex; justify-between; align-items:center;">
                <div class="crop-name" style="font-size:17px; font-weight:800; color:#1b4332;">
                  ${i + 1}. ${crop.crop_name || crop.name}
                </div>
                <span class="confidence-badge" style="background:#1b4332; color:#fff; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:700;">
                  ${matchScore}% ${t('match_label')}
                </span>
              </div>

              ${crop.recommended_variety ? `
                <div style="font-size:13px; font-weight:700; color:#2563eb; margin: 4px 0 6px;">
                  ${t('variety_label')} ${crop.recommended_variety}
                </div>
              ` : ''}

              <div class="confidence-bar-bg" style="height:6px; background:#e5e7eb; border-radius:4px; overflow:hidden; margin-bottom:8px;">
                <div class="confidence-bar-fill" style="width:${matchScore}%; height:100%; background:linear-gradient(90deg, #52b788, #1b4332);"></div>
              </div>

              <div class="crop-tip" style="background:#f8faf9; padding:8px 12px; border-radius:8px; border-left:3px solid #52b788; font-size:12px; color:#374151; margin-bottom:8px;">
                💡 ${crop.suitability_reason || crop.tips}
              </div>

              <div style="display:flex; justify-content:space-between; font-size:12px; color:#4b5563;">
                <span>${t('duration_label')} <strong>${crop.season_duration || '110-120 Days'}</strong></span>
                <span style="color:#059669; font-weight:700;">${t('yield_label')} ${crop.expected_yield_per_acre || '15 Quintal/Acre'}</span>
              </div>
            </div>
          `;
        }).join('')}
      `;
    } else {
      resultsContainer.innerHTML = `<p style="padding:16px;">No recommendations returned.</p>`;
    }
  } catch (err) {
    console.error("Recommendation error:", err);
    resultsContainer.innerHTML = `<p style="color:#dc2626; font-size:13px; padding:16px;">⚠️ Error generating crop recommendations. Please check server connection.</p>`;
  }
}
