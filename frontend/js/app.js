/* AgriSense — Core SPA App Manager + Phone Auth */

const API_BASE = '';  // same-origin (served by FastAPI on Render)

let currentLang = 'gu';   // Default: Gujarati for farmers
let authMode = 'login';   // 'login' | 'register'
let authToken = null;
let currentUser = null;

// ─── Language Helpers ─────────────────────────────────────────────────────────

function getCurrentLanguage() { return currentLang; }

function t(key) {
  return (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key])
      || (TRANSLATIONS['en'][key])
      || key;
}

function updateUILabels() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (key) el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (key) el.placeholder = t(key);
  });
}

function setLanguage(lang) {
  if (!TRANSLATIONS[lang]) return;
  currentLang = lang;

  // Update pill button states
  ['gu','hi','en'].forEach(l => {
    const b = document.getElementById(`lang-btn-${l}`);
    if (b) b.classList.toggle('active', l === lang);
  });

  updateUILabels();
  updateLogoutLabel();

  if (window.currentWeatherData) {
    loadWeatherData(
      window.currentWeatherData.latitude,
      window.currentWeatherData.longitude,
      window.currentWeatherData.location
    );
  }
}

// ─── Auth Language (on auth overlay before login) ─────────────────────────────

function setAuthLang(lang) {
  currentLang = lang;
  document.querySelectorAll('.auth-lang-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = [...document.querySelectorAll('.auth-lang-btn')].find(b => b.getAttribute('onclick') === `setAuthLang('${lang}')`);
  if (activeBtn) activeBtn.classList.add('active');
  renderAuthLabels();
}

function renderAuthLabels() {
  const isReg = authMode === 'register';
  const el = id => document.getElementById(id);

  el('auth-subtitle-text').textContent = t('subtitle');
  el('auth-card-title').textContent = isReg ? t('auth_create') : t('auth_welcome');
  el('auth-phone-label').textContent = '📱 ' + t('auth_phone');
  el('auth-phone').placeholder = t('phone_placeholder');
  if (el('auth-confirm-label')) el('auth-confirm-label').textContent = '📱 ' + t('auth_phone_confirm');
  if (el('auth-phone-confirm')) el('auth-phone-confirm').placeholder = t('confirm_placeholder');
  el('auth-pass-label').textContent = '🔒 ' + t('auth_pass');
  el('auth-submit-btn').textContent = isReg ? t('btn_register') : t('btn_login');
  el('auth-switch-link').textContent = isReg ? t('switch_to_login') : t('switch_to_reg');
  el('auth-confirm-block').style.display = isReg ? 'block' : 'none';
}

function toggleAuthMode() {
  authMode = authMode === 'login' ? 'register' : 'login';
  clearAuthError();
  document.getElementById('auth-phone').value = '';
  document.getElementById('auth-phone-confirm').value = '';
  document.getElementById('auth-password').value = '';
  renderAuthLabels();
}

function showAuthError(msg) {
  const el = document.getElementById('auth-error');
  el.textContent = '❌ ' + msg;
  el.style.display = 'block';
}

function clearAuthError() {
  const el = document.getElementById('auth-error');
  el.style.display = 'none';
  el.textContent = '';
}

// ─── Auth Submit ──────────────────────────────────────────────────────────────

async function handleAuthSubmit() {
  clearAuthError();
  const phone = (document.getElementById('auth-phone').value || '').replace(/\D/g, '');
  const password = document.getElementById('auth-password').value;

  // Validation
  if (!/^[6-9]\d{9}$/.test(phone)) {
    showAuthError(
      currentLang === 'gu' ? 'કૃપા કરી માન્ય ૧૦-અંકનો ભારતીય મોબાઈલ નંબર દાખલ કરો.' :
      currentLang === 'hi' ? 'कृपया सही 10-अंकों का मोबाइल नंबर दर्ज करें।' :
      'Please enter a valid 10-digit Indian mobile number.'
    );
    return;
  }

  if (authMode === 'register') {
    const confirm = (document.getElementById('auth-phone-confirm').value || '').replace(/\D/g, '');
    if (phone !== confirm) {
      showAuthError(
        currentLang === 'gu' ? 'મોબાઈલ નંબર સરખા નથી. ફરીથી ચકાસો.' :
        currentLang === 'hi' ? 'मोबाइल नंबर मेल नहीं खाते। दोबारा जाँचें।' :
        'Mobile numbers do not match. Please re-check.'
      );
      return;
    }
  }

  if (!password || password.length < 4) {
    showAuthError(
      currentLang === 'gu' ? 'પાસવર્ડ ઓછામાં ઓછો ૪ અક્ષરનો હોવો જોઈએ.' :
      currentLang === 'hi' ? 'पासवर्ड कम से कम 4 अक्षर का होना चाहिए।' :
      'Password must be at least 4 characters.'
    );
    return;
  }

  // Set loading state
  const btn = document.getElementById('auth-submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spinner"></span>';

  try {
    const endpoint = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: phone, password })
    });
    const data = await res.json();

    if (!res.ok) {
      showAuthError(data.detail || data.error || 'Request failed. Please try again.');
      return;
    }

    // Store session
    authToken = data.token;
    currentUser = { user_id: data.user_id, username: data.username || phone };
    localStorage.setItem('agrisense_token', data.token);
    localStorage.setItem('agrisense_user', JSON.stringify(currentUser));

    if (authMode === 'register') {
      showRegSuccess(phone);
    } else {
      enterApp();
    }

  } catch (e) {
    showAuthError(
      currentLang === 'gu' ? 'સર્વર સાથે જોડાઈ શક્યા નહિ. ઇન્ટરનેટ તપાસો.' :
      currentLang === 'hi' ? 'सर्वर से कनेक्ट नहीं हो सका। इंटरनेट जाँचें।' :
      'Could not connect to server. Please check your internet connection.'
    );
  } finally {
    btn.disabled = false;
    renderAuthLabels();
  }
}

// ─── Registration Success Screen ───────────────────────────────────────────────

function showRegSuccess(phone) {
  const masked = 'XXXXXXX' + String(phone).slice(-3);
  document.getElementById('auth-overlay').classList.add('hidden');

  // Translate success text
  document.getElementById('success-title').textContent =
    currentLang === 'gu' ? 'ખાતું સફળતાપૂર્વક બન્યું!' :
    currentLang === 'hi' ? 'खाता सफलतापूर्वक बनाया गया!' :
    'Account Created Successfully!';

  document.getElementById('success-phone-label').textContent =
    currentLang === 'gu' ? 'નોંધાયેલ મોબાઈલ નંબર' :
    currentLang === 'hi' ? 'पंजीकृत मोबाइल नंबर' :
    'Registered Mobile Number';

  document.getElementById('success-phone-num').textContent = '📱 ' + masked;

  document.getElementById('success-desc').textContent =
    currentLang === 'gu' ? 'તમારો AgriSense ખાતો તૈયાર છે. "Open App" દબાવો અને AI ખેતી સહાય મેળવો.' :
    currentLang === 'hi' ? 'आपका AgriSense खाता तैयार है। "Open App" दबाएं और AI कृषि सहायता प्राप्त करें।' :
    'Your AgriSense account is ready. Click "Open App" to get AI farming assistance.';

  document.getElementById('reg-success-overlay').classList.remove('hidden');
}

// ─── Enter App ────────────────────────────────────────────────────────────────

function enterApp() {
  document.getElementById('auth-overlay').classList.add('hidden');
  document.getElementById('reg-success-overlay').classList.add('hidden');
  document.getElementById('app-frame').style.display = 'block';

  // Sync language to main app
  setLanguage(currentLang);

  // Show logged-in phone in Profile
  if (currentUser) {
    const phoneEl = document.getElementById('logout-phone-display');
    if (phoneEl) phoneEl.textContent = currentUser.username || '';
    const profPhone = document.getElementById('prof-phone');
    if (profPhone) profPhone.value = currentUser.username || '';
  }

  updateLogoutLabel();
  loadWeatherData();
  loadProfileData();
}

// ─── Logout ───────────────────────────────────────────────────────────────────

function handleLogout() {
  const confirmMsg =
    currentLang === 'gu' ? 'શું તમે ખરેખર લૉગઆઉટ કરવા માંગો છો?' :
    currentLang === 'hi' ? 'क्या आप वाकई लॉगआउट करना चाहते हैं?' :
    'Are you sure you want to log out?';

  if (!confirm(confirmMsg)) return;

  localStorage.removeItem('agrisense_token');
  localStorage.removeItem('agrisense_user');
  authToken = null;
  currentUser = null;
  authMode = 'login';

  // Reset form fields
  document.getElementById('auth-phone').value = '';
  document.getElementById('auth-phone-confirm').value = '';
  document.getElementById('auth-password').value = '';
  clearAuthError();

  document.getElementById('app-frame').style.display = 'none';
  document.getElementById('auth-overlay').classList.remove('hidden');
  renderAuthLabels();
}

function updateLogoutLabel() {
  const el = document.getElementById('logout-label');
  if (el) el.textContent =
    currentLang === 'gu' ? 'લૉગઆઉટ' :
    currentLang === 'hi' ? 'लॉगआउट' : 'Logout';
}

// ─── Auth Header Helper (for API calls) ──────────────────────────────────────

function getAuthHeaders(extra = {}) {
  const headers = { 'Content-Type': 'application/json', ...extra };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  return headers;
}

// ─── Tab Navigation ───────────────────────────────────────────────────────────

function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetNav = document.getElementById(`nav-${tabId}`);

  if (targetTab) targetTab.classList.add('active');
  if (targetNav) targetNav.classList.add('active');

  if (tabId === 'weather' && !window.currentWeatherData) loadWeatherData();
  else if (tabId === 'profile') loadProfileData();
}

// ─── Toast ────────────────────────────────────────────────────────────────────

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

// ─── Slider Sync ──────────────────────────────────────────────────────────────

function syncSlider(inputId, spanId) {
  const val = document.getElementById(inputId).value;
  document.getElementById(spanId).textContent = val;
}

// ─── App Initialization ───────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Check saved session
  const savedToken = localStorage.getItem('agrisense_token');
  const savedUser = localStorage.getItem('agrisense_user');

  if (savedToken && savedUser) {
    authToken = savedToken;
    try { currentUser = JSON.parse(savedUser); } catch(e) { currentUser = null; }
    if (currentUser) {
      enterApp();
      return;
    }
  }

  // Show auth screen with default language Gujarati
  setAuthLang('gu');
  renderAuthLabels();
});
