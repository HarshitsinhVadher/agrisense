/* Weather & Geocoding UI Component (Matches Mobile App.js 1:1) */

window.currentWeatherData = null;
window.currentLat = 22.57;
window.currentLon = 72.93;
window.currentLocationName = "Anand, Gujarat";

async function loadWeatherData(lat = window.currentLat, lon = window.currentLon, locName = window.currentLocationName) {
  window.currentLat = lat;
  window.currentLon = lon;
  window.currentLocationName = locName;

  const hero = document.getElementById('weather-hero');
  if (hero) {
    hero.innerHTML = `
      <div class="spinner"></div>
      <p style="margin-top:8px; font-size:13px;">${t('app_title')} — Fetching weather for ${locName}...</p>
    `;
  }

  try {
    const res = await fetch(`/api/weather?lat=${lat}&lon=${lon}&location_name=${encodeURIComponent(locName)}`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    window.currentWeatherData = data;
    renderWeatherHero(data, locName);
    renderAdvisories(data.advisories);
    renderForecast(data.daily_forecast);

    // Trigger soil location data fetch for Crop AI tab
    if (typeof fetchLocationSoilData === 'function') {
      fetchLocationSoilData(lat, lon, locName);
    }
  } catch (err) {
    console.error("Weather fetch error:", err);
    if (hero) {
      hero.innerHTML = `<p style="color:#fecaca;">⚠️ Could not load weather data for ${locName}.</p>`;
    }
  }
}

function renderWeatherHero(data, locName) {
  const hero = document.getElementById('weather-hero');
  if (!hero) return;

  const curr = data.current || {};
  const temp = curr.temperature !== undefined ? Math.round(curr.temperature) : '--';
  const cond = curr.condition || 'Clear';
  const icon = cond.toLowerCase().includes('rain') ? '🌧️' : cond.toLowerCase().includes('cloud') ? '⛅' : '☀️';

  hero.innerHTML = `
    <div class="location-badge">📍 ${locName}</div>
    <div class="temp-large">
      <span class="weather-icon">${icon}</span>
      <span>${temp}°C</span>
    </div>
    <p style="font-size:14px; color:#b7e4c7; font-weight:600;">${cond}</p>

    <div class="weather-stats">
      <div class="stat-item">
        <div>💧 ${t('humidity')}</div>
        <div class="stat-val">${curr.humidity || '--'}%</div>
      </div>
      <div class="stat-item">
        <div>💨 ${t('wind')}</div>
        <div class="stat-val">${curr.wind_speed || '--'} km/h</div>
      </div>
      <div class="stat-item">
        <div>🌧️ ${t('rainfall')}</div>
        <div class="stat-val">${curr.rainfall !== undefined ? curr.rainfall : 0} mm</div>
      </div>
    </div>
  `;

  // Update target region badge in Crop AI tab if present
  const regBadge = document.getElementById('crop-target-region-display');
  if (regBadge) regBadge.textContent = `${t('target_region')} ${locName}`;
}

function renderAdvisories(advisories) {
  const container = document.getElementById('advisories-container');
  if (!container) return;

  if (!advisories || advisories.length === 0) {
    container.innerHTML = `<p style="font-size:13px; color:#6b7280;">No active advisories for this region.</p>`;
    return;
  }

  container.innerHTML = advisories.map(adv => {
    const title = typeof adv === 'string' ? adv : (adv.title || adv);
    const desc = typeof adv === 'object' && adv.description ? adv.description : '';
    return `
      <div class="advisory-card caution">
        <div class="advisory-title">📢 ${title}</div>
        ${desc ? `<div class="advisory-msg">${desc}</div>` : ''}
      </div>
    `;
  }).join('');
}

function renderForecast(forecast) {
  const container = document.getElementById('forecast-container');
  if (!container) return;

  if (!forecast || forecast.length === 0) {
    container.innerHTML = `<p style="font-size:13px; color:#6b7280;">Forecast data unavailable.</p>`;
    return;
  }

  container.innerHTML = forecast.map(day => {
    const icon = (day.condition || '').toLowerCase().includes('rain') ? '🌧️' : '☀️';
    return `
      <div class="forecast-item">
        <div class="forecast-day">${day.day || day.date}</div>
        <div class="forecast-icon">${icon}</div>
        <div class="forecast-temp">${Math.round(day.max_temp || day.temp)}° / ${Math.round(day.min_temp || (day.temp - 5))}°</div>
      </div>
    `;
  }).join('');
}

// ─── GPS Location Fetch ───
function useGPSLocationWeb() {
  if (!navigator.geolocation) {
    showToast("⚠️ Geolocation is not supported by your browser.");
    return;
  }
  showToast("📍 Fetching GPS Location...");
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      let locName = `GPS (${lat.toFixed(2)}, ${lon.toFixed(2)})`;

      try {
        const res = await fetch(`/api/geocode?lat=${lat}&lon=${lon}`);
        const data = await res.json();
        if (data && data.display) locName = data.display;
      } catch(e) {}

      loadWeatherData(lat, lon, locName);
      showToast(`📍 Location updated: ${locName}`);
    },
    (err) => {
      showToast("⚠️ Could not access GPS location. Please search a city.");
    }
  );
}

// ─── City Search Geocoding ───
async function handleCitySearch() {
  const query = (document.getElementById('city-search-input')?.value || '').trim();
  if (!query || query.length < 2) return;

  const resultsDiv = document.getElementById('city-search-results');
  if (resultsDiv) resultsDiv.innerHTML = `<p style="font-size:12px; color:#6b7280;">Searching cities...</p>`;

  try {
    const res = await fetch(`/api/geocode?query=${encodeURIComponent(query)}`);
    const data = await res.json();
    const cities = data.results || [];

    if (cities.length === 0) {
      if (resultsDiv) resultsDiv.innerHTML = `<p style="font-size:12px; color:#ef4444;">No cities found matching "${query}".</p>`;
      return;
    }

    if (resultsDiv) {
      resultsDiv.innerHTML = cities.map(c => `
        <div class="city-result-item" onclick="selectSearchedCity(${c.latitude}, ${c.longitude}, '${c.display.replace(/'/g, "\\'")}')">
          <strong>📍 ${c.display}</strong>
          <span style="font-size:11px; color:#6b7280;">(Lat: ${c.latitude.toFixed(2)}, Lon: ${c.longitude.toFixed(2)})</span>
        </div>
      `).join('');
    }
  } catch (err) {
    if (resultsDiv) resultsDiv.innerHTML = `<p style="font-size:12px; color:#ef4444;">City search failed.</p>`;
  }
}

function selectSearchedCity(lat, lon, locName) {
  const resultsDiv = document.getElementById('city-search-results');
  if (resultsDiv) resultsDiv.innerHTML = '';
  const input = document.getElementById('city-search-input');
  if (input) input.value = '';

  loadWeatherData(lat, lon, locName);
  showToast(`📍 Location set to ${locName}`);
}
