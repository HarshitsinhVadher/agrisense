/* AgriSense Core SPA Application Manager */
let currentLang = 'en';

function getCurrentLanguage() {
  return currentLang;
}

function setLanguage(lang) {
  if (TRANSLATIONS[lang]) {
    currentLang = lang;
    document.getElementById('lang-select').value = lang;
    updateUILabels();
    // Refresh weather advisories and label scan summary with new language
    if (window.currentWeatherData) {
      loadWeatherData(window.currentWeatherData.latitude, window.currentWeatherData.longitude, window.currentWeatherData.location);
    }
  }
}

function t(key) {
  return (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) || (TRANSLATIONS['en'][key]) || key;
}

function updateUILabels() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (key) {
      el.textContent = t(key);
    }
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (key) {
      el.placeholder = t(key);
    }
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetTab) targetTab.classList.add('active');
  if (targetNav) targetNav.classList.add('active');

  // Trigger tab-specific data refresh
  if (tabId === 'weather' && !window.currentWeatherData) {
    loadWeatherData();
  } else if (tabId === 'profile') {
    loadProfileData();
  }
}

function showToast(msg) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Language Change listener
  const langSelect = document.getElementById('lang-select');
  if (langSelect) {
    langSelect.addEventListener('change', (e) => setLanguage(e.target.value));
  }

  // Load initial data
  updateUILabels();
  loadWeatherData();
  autofillFromSoilCard();
});
