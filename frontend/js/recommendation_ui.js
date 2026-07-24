/* Crop Recommendation UI Component */

function syncSlider(sliderId, valId) {
  const slider = document.getElementById(sliderId);
  const valDisplay = document.getElementById(valId);
  if (slider && valDisplay) {
    valDisplay.textContent = slider.value;
  }
}

async function autofillFromSoilCard() {
  try {
    const res = await fetch('/api/profile');
    const profile = await res.json();
    if (profile) {
      document.getElementById('input-N').value = profile.N || 180;
      document.getElementById('input-P').value = profile.P || 42;
      document.getElementById('input-K').value = profile.K || 160;
      document.getElementById('input-ph').value = profile.pH || 7.2;

      syncSlider('input-N', 'val-N');
      syncSlider('input-P', 'val-P');
      syncSlider('input-K', 'val-K');
      syncSlider('input-ph', 'val-ph');

      showToast("📋 Soil parameters loaded from Profile/Soil Card!");
    }
  } catch (err) {
    showToast("⚠️ Could not load profile soil data.");
  }
}

function autofillFromWeather() {
  if (window.currentWeatherData && window.currentWeatherData.current) {
    const curr = window.currentWeatherData.current;
    document.getElementById('input-temp').value = curr.temperature.toFixed(1);
    document.getElementById('input-humidity').value = curr.humidity;
    syncSlider('input-temp', 'val-temp');
    syncSlider('input-humidity', 'val-humidity');
    showToast("🌤️ Temperature & Humidity auto-filled from Weather!");
  } else {
    showToast("⚠️ Weather data not loaded yet.");
  }
}

async function submitCropRecommendation(e) {
  if (e) e.preventDefault();

  const N = parseFloat(document.getElementById('input-N').value);
  const P = parseFloat(document.getElementById('input-P').value);
  const K = parseFloat(document.getElementById('input-K').value);
  const ph = parseFloat(document.getElementById('input-ph').value);
  const temperature = parseFloat(document.getElementById('input-temp').value);
  const humidity = parseFloat(document.getElementById('input-humidity').value);
  const rainfall = parseFloat(document.getElementById('input-rain').value);

  const resultsContainer = document.getElementById('recommend-results');
  resultsContainer.innerHTML = `<div style="text-align:center; padding:20px;"><div class="spinner"></div><p style="margin-top:8px; font-size:13px; color:#1b4332;">Running Random Forest Classifier...</p></div>`;

  try {
    const res = await fetch('/api/recommend-crop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ N, P, K, ph, temperature, humidity, rainfall })
    });
    const data = await res.json();

    if (data.recommendations && data.recommendations.length > 0) {
      resultsContainer.innerHTML = `
        <h3 class="card-title" style="margin-top:10px;">${t('recommend_results_title')}</h3>
        ${data.recommendations.map((rec, i) => `
          <div class="result-crop-card ${i === 0 ? 'rank-1' : ''}">
            <div class="crop-header">
              <div class="crop-name">${i + 1}. ${rec.name}</div>
              <div class="confidence-badge">${rec.confidence}% Match</div>
            </div>
            <div class="confidence-bar-bg">
              <div class="confidence-bar-fill" style="width: ${rec.confidence}%;"></div>
            </div>
            <div class="crop-details-grid">
              <div><strong>Category:</strong> ${rec.category}</div>
              <div><strong>Season:</strong> ${rec.season}</div>
              <div><strong>Water Need:</strong> ${rec.water_requirement}</div>
              <div><strong>Crop ID:</strong> ${rec.crop_id}</div>
            </div>
            <div class="crop-tip">
              💡 <strong>Agronomic Tip:</strong> ${rec.tips}
            </div>
          </div>
        `).join('')}
      `;
    } else {
      resultsContainer.innerHTML = `<p>No recommendations returned.</p>`;
    }
  } catch (err) {
    console.error("Recommendation error:", err);
    resultsContainer.innerHTML = `<p style="color:red; font-size:13px;">⚠️ Error generating recommendations.</p>`;
  }
}
