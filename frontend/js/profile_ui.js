/* Profile & Scan History UI Component */

async function loadProfileData() {
  try {
    const res = await fetch('/api/profile');
    const profile = await res.json();

    document.getElementById('prof-name').value = profile.name || 'Ramesh Patel';
    document.getElementById('prof-phone').value = profile.phone || '+91 98765 43210';
    document.getElementById('prof-location').value = profile.location || 'Anand, Gujarat';
    document.getElementById('prof-soil-type').value = profile.soil_type || 'Loamy Soil';

    if (profile.preferred_language) {
      document.getElementById('lang-select').value = profile.preferred_language;
    }
  } catch (err) {
    console.error("Profile fetch error:", err);
  }

  loadScanHistory();
}

async function saveProfileData(e) {
  if (e) e.preventDefault();

  const name = document.getElementById('prof-name').value;
  const phone = document.getElementById('prof-phone').value;
  const location = document.getElementById('prof-location').value;
  const soil_type = document.getElementById('prof-soil-type').value;
  const preferred_language = getCurrentLanguage();

  try {
    const currRes = await fetch('/api/profile');
    const profile = await currRes.json();

    profile.name = name;
    profile.phone = phone;
    profile.location = location;
    profile.soil_type = soil_type;
    profile.preferred_language = preferred_language;

    await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile)
    });

    showToast("💾 Farmer Profile updated!");
  } catch (err) {
    showToast("⚠️ Could not update profile.");
  }
}

async function loadScanHistory() {
  const container = document.getElementById('history-container');
  if (!container) return;

  try {
    const res = await fetch('/api/history');
    const history = await res.json();

    if (history && history.length > 0) {
      container.innerHTML = history.map(item => `
        <div class="card" style="padding:12px; margin-bottom:8px; border-left:3px solid var(--accent);">
          <div style="font-size:13px; font-weight:700; color:var(--primary);">${item.title}</div>
          <div style="font-size:11px; color:#6b7280;">${item.created_at} | Type: ${item.scan_type}</div>
        </div>
      `).join('');
    } else {
      container.innerHTML = `<p style="font-size:12px; color:#6b7280;">No recent scan history.</p>`;
    }
  } catch (err) {
    console.error("History fetch error:", err);
  }
}
