/* Weather & Advisory UI Component */
async function loadWeatherData(lat = 22.57, lon = 72.93, locationName = "Anand, Gujarat") {
  const heroEl = document.getElementById("weather-hero");
  const advisoriesEl = document.getElementById("advisories-container");
  const forecastEl = document.getElementById("forecast-container");

  if (!heroEl) return;

  try {
    const res = await fetch(`/api/weather?lat=${lat}&lon=${lon}&location_name=${encodeURIComponent(locationName)}`);
    const data = await res.json();
    window.currentWeatherData = data;

    // Render Hero Card
    heroEl.innerHTML = `
      <div class="location-badge">📍 ${data.location}</div>
      <div class="temp-large">
        <span class="weather-icon">${data.current.icon}</span>
        <span>${data.current.temperature.toFixed(1)}°C</span>
      </div>
      <p style="font-weight:600; font-size:14px; opacity:0.9;">${data.current.description}</p>
      <div class="weather-stats">
        <div class="stat-item">
          <div>${t('humidity')}</div>
          <div class="stat-val">💧 ${data.current.humidity}%</div>
        </div>
        <div class="stat-item">
          <div>${t('wind')}</div>
          <div class="stat-val">💨 ${data.current.wind_speed} km/h</div>
        </div>
        <div class="stat-item">
          <div>${t('feels_like')}</div>
          <div class="stat-val">🌡️ ${data.current.apparent_temp.toFixed(1)}°C</div>
        </div>
      </div>
    `;

    // Render Agricultural Advisories
    const lang = getCurrentLanguage();
    if (data.advisories && data.advisories.length > 0) {
      advisoriesEl.innerHTML = data.advisories.map(adv => {
        const title = adv[`title_${lang}`] || adv.title;
        const msg = adv[`message_${lang}`] || adv.message;
        return `
          <div class="advisory-card ${adv.type || 'info'}">
            <div class="advisory-title">${title}</div>
            <div class="advisory-msg">${msg}</div>
          </div>
        `;
      }).join('');
    } else {
      advisoriesEl.innerHTML = `<p style="font-size:12px; color:#666;">No active advisories.</p>`;
    }

    // Render 7-Day Forecast
    if (data.forecast && data.forecast.length > 0) {
      forecastEl.innerHTML = data.forecast.map((f, i) => `
        <div class="forecast-item">
          <div class="forecast-day">${i === 0 ? 'Today' : f.date}</div>
          <div class="forecast-icon">${f.icon}</div>
          <div class="forecast-temp">${f.max_temp.toFixed(0)}° / ${f.min_temp.toFixed(0)}°</div>
          <div style="font-size:10px; color:#6b7280; margin-top:3px;">🌧️ ${f.precip_prob}%</div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error("Weather load error:", err);
    showToast("⚠️ Weather data update failed.");
  }
}

function searchLocation() {
  const city = prompt("Enter City / Location Name:", "Anand, Gujarat");
  if (city) {
    // Basic coordinate mapping for common locations
    let lat = 22.57, lon = 72.93;
    const lower = city.toLowerCase();
    if (lower.includes("ahmedabad")) { lat = 23.02; lon = 72.57; }
    else if (lower.includes("rajkot")) { lat = 22.30; lon = 70.80; }
    else if (lower.includes("surat")) { lat = 21.17; lon = 72.83; }
    else if (lower.includes("vadodara")) { lat = 22.30; lon = 73.18; }
    else if (lower.includes("junagadh")) { lat = 21.52; lon = 70.45; }
    
    loadWeatherData(lat, lon, city);
  }
}
