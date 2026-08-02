import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, TextInput, Modal, ActivityIndicator, Alert, Animated, Dimensions, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import Constants from 'expo-constants';
import CameraScanner from './components/CameraScanner';

// Live 24/7 Render Cloud Backend Endpoint
const API_BASE_URL = 'https://agrisense-00qs.onrender.com';

const TRANSLATIONS = {
  en: {
    app_title: "AgriSense", subtitle: "AI-Powered Farming Assistant",
    tab_weather: "Weather", tab_recommend: "Crop AI", tab_scan: "Label Scanner", tab_profile: "Profile",
    weather_title: "Weather & 3-Month Forecast", set_location: "📍 Set Location", use_gps: "📍 Use My GPS Location", search_city: "Or search a city:",
    advisories_title: "📢 Agricultural Advisories", seasonal_title: "🗓️ 3-Month Seasonal Forecast", forecast_7day: "📅 7-Day Weather Forecast",
    scanner_title: "🏷️ AI Label Scanner", scanner_sub: "Powered by Gemini Vision AI — Take a photo of any pesticide, fertilizer, or seed package",
    take_photo: "📷 Take Photo of Product", capture_sub: "Capture the label, bag, or bottle", type_product: "Or type product name (e.g. Urea, Chlorpyrifos, Ferterra)",
    analyze_btn: "🔍 Analyze Product", confidence: "Confidence", brand: "Manufacturer / Brand", active: "Active Ingredient", dosage: "Dosage / Directions",
    crop_title: "🌱 AI Crop Recommender", crop_sub: "Random Forest ML model trained on 2,200 soil-climate profiles", predict_btn: "🌱 Predict Suitable Crops",
    water_req: "Water Requirement", season: "Optimal Season", tips: "Agricultural Tip", profile_title: "👨‍🌾 Farmer Profile & Settings", save_profile: "💾 Save Profile",
    auth_welcome: "Farmer Login", auth_create: "Create Farmer Account",
    auth_phone: "Mobile Number (10 Digits)", auth_phone_confirm: "Re-type Mobile Number", auth_pass: "Password",
    phone_placeholder: "Enter 10-digit mobile number", confirm_placeholder: "Re-enter 10-digit mobile number",
    btn_login: "🔓 Login", btn_register: "📝 Register Account",
    switch_to_reg: "Don't have an account? Register here", switch_to_login: "Already have an account? Login here"
  },
  gu: {
    app_title: "એગ્રીસેન્સ", subtitle: "એઆઈ આધારિત ડિજિટલ ખેડૂત સહાયક",
    tab_weather: "હવામાન", tab_recommend: "પાક પસંદગી", tab_scan: "દવા સ્કેનર", tab_profile: "પ્રોફાઇલ",
    weather_title: "હવામાન અને ૩-મહિનાનું મોસમી અનુમાન", set_location: "📍 ગામ / સ્થળ પસંદ કરો", use_gps: "📍 જીપીએસ દ્વારા મારું ખેતર શોધો", search_city: "અથવા તાલુકો/શહેર શોધો:",
    advisories_title: "📢 કૃષિ સલાહ અને ખેતી માર્ગદર્શન", seasonal_title: "🗓️ ૩-મહિનાનું વરસાદી અનુમાન", forecast_7day: "📅 ૭-દિવસનું હવામાન અનુમાન",
    scanner_title: "🏷️ એઆઈ દવા અને ખાતર સ્કેનર", scanner_sub: "જેમિનાઈ વિઝન એઆઈ — જંતુનાશક દવા, ખાતર કે બિયારણનો ફોટો પાડી વિગતો મેળવો",
    take_photo: "📷 દવા કે ખાતરના થેલાનો ફોટો લો", capture_sub: "બોટલ, થેલી કે લેબલનો ફોટો પાડો", type_product: "અથવા દવાનું નામ લખો (દા.ત. ફેર્ટેરા, યુરિયા, કોરાજન)",
    analyze_btn: "🔍 દવા વિશ્લેષણ કરો", confidence: "ચોકસાઈ", brand: "ઉત્પાદક / બ્રાન્ડ", active: "સક્રિય રાસાયણિક ઘટક", dosage: "છંટકાવ / વાવણીનો સાચો ડોઝ",
    crop_title: "🌱 એઆઈ જમીન-હવામાન પાક ભલામણ", crop_sub: "ગુજરાતના ૨૬ જિલ્લાઓ અને જમીન ડેટા આધારિત ભલામણ", predict_btn: "🌱 ખેતર માટે યોગ્ય પાક જુઓ",
    water_req: "પાણીની જરૂરિયાત", season: "વાવણીની ઋતુ", tips: "ખેતી સલાહ", profile_title: "👨‍🌾 ખેડૂત પ્રોફાઇલ અને માહિતી", save_profile: "💾 વિગતો સાચવો",
    auth_welcome: "ખેડૂત લોગિન", auth_create: "નવું ખેડૂત ખાતું બનાવો",
    auth_phone: "૧૦-અંકનો મોબાઈલ નંબર", auth_phone_confirm: "મોબાઈલ નંબર ફરીથી લખો", auth_pass: "ગુપ્ત પાસવર્ડ",
    phone_placeholder: "૧૦-અંકનો મોબાઈલ નંબર દાખલ કરો", confirm_placeholder: "મોબાઈલ નંબર ફરીથી દાખલ કરો",
    btn_login: "🔓 પ્રવેશ કરો (લોગિન)", btn_register: "📝 નવું ખાતું બનાવો",
    switch_to_reg: "ખાતું નથી? અહીં નવું ખાતું બનાવો", switch_to_login: "ખાતું છે? અહીં પ્રવેશ કરો"
  },
  hi: {
    app_title: "एग्रीसेंस", subtitle: "एआई संचालित कृषि सहायक",
    tab_weather: "मौसम", tab_recommend: "फसल चयन", tab_scan: "दवा स्कैनर", tab_profile: "प्रोफ़ाइल",
    weather_title: "मौसम और 3-महीने का पूर्वानुमान", set_location: "📍 स्थान चुनें", use_gps: "📍 जीपीएस स्थान का उपयोग करें", search_city: "या शहर/तहसील खोजें:",
    advisories_title: "📢 कृषि सलाह और मार्गदर्शन", seasonal_title: "🗓️ 3-महीने का मौसमी पूर्वानुमान", forecast_7day: "📅 7-दिवसीय मौसम पूर्वानुमान",
    scanner_title: "🏷️ एआई दवा एवं खाद स्कैनर", scanner_sub: "जेमिनी विजन एआई — कीटनाशक, खाद या बीज का फोटो खींचकर जानकारी पाएं",
    take_photo: "📷 उत्पाद लेबल का फोटो लें", capture_sub: "बोतल, पैकेट या बैग का फोटो लें", type_product: "या उत्पाद का नाम लिखें (जैसे यूरिया, फेरटेरा, कोराजन)",
    analyze_btn: "🔍 विश्लेषण करें", confidence: "सटीकता", brand: "निर्माता / ब्रांड", active: "सक्रिय रासायनिक घटक", dosage: "छिड़काव / खुराक का प्रमाण",
    crop_title: "🌱 एआई फसल सिफारिश", crop_sub: "मृदा और जलवायु डेटा पर आधारित सटीक सिफारिश", predict_btn: "🌱 उपयुक्त फसलों की सिफारिश देखें",
    water_req: "पानी की आवश्यकता", season: "बुआई का मौसम", tips: "कृषि सलाह", profile_title: "👨‍🌾 किसान प्रोफ़ाइल", save_profile: "💾 विवरण सहेजें",
    auth_welcome: "किसान लॉगिन", auth_create: "नया किसान खाता बनाएं",
    auth_phone: "10-अंकों का मोबाइल नंबर", auth_phone_confirm: "मोबाइल नंबर पुनः दर्ज करें", auth_pass: "पासवर्ड",
    phone_placeholder: "10-अंकों का मोबाइल नंबर दर्ज करें", confirm_placeholder: "मोबाइल नंबर दोबारा दर्ज करें",
    btn_login: "🔓 लॉगिन करें", btn_register: "📝 नया खाता बनाएं",
    switch_to_reg: "खाता नहीं है? यहां नया खाता बनाएं", switch_to_login: "खाता है? यहां लॉगिन करें"
  }
};

function t(key, lang = 'en') {
  return (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) || (TRANSLATIONS['en'] && TRANSLATIONS['en'][key]) || key;
}

export default function App() {
  // ─── Auth State ───
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authToken, setAuthToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [authScreen, setAuthScreen] = useState('login'); // 'login' or 'register'
  const [authPhone, setAuthPhone] = useState('');
  const [authPhoneConfirm, setAuthPhoneConfirm] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [checkingAuth, setCheckingAuth] = useState(true);

  // ─── App State ───
  const [activeTab, setActiveTab] = useState('weather');
  const [lang, setLang] = useState('gu'); // Default to Gujarati for farmers

  // ─── Weather State ───
  const [weather, setWeather] = useState(null);
  const [weatherLat, setWeatherLat] = useState(22.57);
  const [weatherLon, setWeatherLon] = useState(72.93);
  const [weatherLocation, setWeatherLocation] = useState('Anand, Gujarat');
  const [cityQuery, setCityQuery] = useState('');
  const [cityResults, setCityResults] = useState([]);
  const [citySearching, setCitySearching] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);

  // ─── Crop Recommendation State ───
  const [nVal, setNVal] = useState('');
  const [pVal, setPVal] = useState('');
  const [kVal, setKVal] = useState('');
  const [phVal, setPhVal] = useState('');
  const [tempVal, setTempVal] = useState('26');
  const [humVal, setHumVal] = useState('75');
  const [rainVal, setRainVal] = useState('110');
  const [selectedSoilType, setSelectedSoilType] = useState('Auto-Detect');
  const [recommendations, setRecommendations] = useState(null);
  const [aiPlanResult, setAiPlanResult] = useState(null);
  const [recLoading, setRecLoading] = useState(false);
  const [zoneInfo, setZoneInfo] = useState(null);

  // ─── Label Scanner State ───
  const [labelText, setLabelText] = useState('');
  const [labelResult, setLabelResult] = useState(null);
  const [labelLoading, setLabelLoading] = useState(false);
  const [scanStep, setScanStep] = useState(0);

  // ─── Camera Modal State ───
  const [cameraVisible, setCameraVisible] = useState(false);

  // ─── Farmer Profile State ───
  const [farmerName, setFarmerName] = useState('');
  const [farmerPhone, setFarmerPhone] = useState('');
  const [farmerLocation, setFarmerLocation] = useState('');

  // ─── Animations ───
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // ─── Auth Headers ───
  const authHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    return headers;
  };

  // ─── On App Launch ───
  useEffect(() => {
    checkSavedAuth();
  }, []);

  const checkSavedAuth = async () => {
    try {
      const savedToken = await AsyncStorage.getItem('agrisense_token');
      const savedUser = await AsyncStorage.getItem('agrisense_user');
      if (savedToken && savedUser) {
        setAuthToken(savedToken);
        setCurrentUser(JSON.parse(savedUser));
        setIsLoggedIn(true);
      }
    } catch (e) {
      console.log("Auth check error:", e);
    } finally {
      setCheckingAuth(false);
    }
  };

  // ─── Fetch data after login ───
  useEffect(() => {
    if (isLoggedIn && authToken) {
      fetchWeather(weatherLat, weatherLon, weatherLocation);
      fetchProfile();
      fetchLocationSoilData(weatherLat, weatherLon, weatherLocation);
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
    }
  }, [isLoggedIn, authToken]);

  // ─── Auth: Phone Number Validation Helper ───
  const isValidIndianPhone = (phoneStr) => {
    const clean = (phoneStr || '').replace(/\D/g, '');
    return clean.length === 10 && /^[6-9]\d{9}$/.test(clean);
  };

  // ─── Auth: Register ───
  const handleRegister = async () => {
    setAuthError('');
    const cleanPhone = authPhone.replace(/\D/g, '');
    const cleanConfirm = authPhoneConfirm.replace(/\D/g, '');

    if (!isValidIndianPhone(cleanPhone)) {
      setAuthError(lang === 'gu' ? 'કૃપા કરીને માન્ય ૧૦-અંકનો મોબાઈલ નંબર લખો.' : 'Please enter a valid 10-digit Indian mobile number.');
      return;
    }

    if (cleanPhone !== cleanConfirm) {
      setAuthError(lang === 'gu' ? 'મોબાઈલ નંબર સરખા નથી. કૃપા કરીને ચકાસીને ફરી લખો.' : 'Mobile numbers do not match. Please re-check and type again.');
      return;
    }

    if (!authPassword || authPassword.length < 4) {
      setAuthError(lang === 'gu' ? 'પાસવર્ડ ઓછામાં ઓછો ૪ અક્ષરનો હોવો જોઈએ.' : 'Password must be at least 4 characters.');
      return;
    }

    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: cleanPhone, password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) { setAuthError(data.detail || data.error || 'Registration failed'); return; }

      await AsyncStorage.setItem('agrisense_token', data.token);
      await AsyncStorage.setItem('agrisense_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
      setAuthToken(data.token);
      setCurrentUser({ user_id: data.user_id, username: data.username });
      setIsLoggedIn(true);
    } catch (e) {
      setAuthError('Could not connect to server. Please check internet connection.');
    } finally {
      setAuthLoading(false);
    }
  };

  // ─── Auth: Login ───
  const handleLogin = async () => {
    setAuthError('');
    const cleanPhone = authPhone.replace(/\D/g, '');

    if (!isValidIndianPhone(cleanPhone)) {
      setAuthError(lang === 'gu' ? 'કૃપા કરીને તમારો ૧૦-અંકનો મોબાઈલ નંબર લખો.' : 'Enter your 10-digit registered mobile number.');
      return;
    }
    if (!authPassword) {
      setAuthError(lang === 'gu' ? 'પાસવર્ડ દાખલ કરો.' : 'Please enter your password.');
      return;
    }

    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: cleanPhone, password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) { setAuthError(data.detail || data.error || 'Login failed'); return; }

      await AsyncStorage.setItem('agrisense_token', data.token);
      await AsyncStorage.setItem('agrisense_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
      setAuthToken(data.token);
      setCurrentUser({ user_id: data.user_id, username: data.username });
      setIsLoggedIn(true);
    } catch (e) {
      setAuthError('Could not connect to server. Please check internet connection.');
    } finally {
      setAuthLoading(false);
    }
  };

  // ─── Auth: Logout ───
  const handleLogout = async () => {
    await AsyncStorage.removeItem('agrisense_token');
    await AsyncStorage.removeItem('agrisense_user');
    setAuthToken(null);
    setCurrentUser(null);
    setIsLoggedIn(false);
    setAuthPhone('');
    setAuthPhoneConfirm('');
    setAuthPassword('');
    setAuthScreen('login');
    fadeAnim.setValue(0);
  };

  // ─── Weather: Fetch ───
  const fetchWeather = async (lat, lon, locName) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/weather?lat=${lat}&lon=${lon}&location_name=${encodeURIComponent(locName)}`, {
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });
      const data = await res.json();
      setWeather(data);
    } catch (e) { console.log("Weather fetch error:", e); }
  };

  // ─── Weather: GPS Location ───
  const useGPSLocation = async () => {
    setGpsLoading(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') { Alert.alert('Permission Denied', 'Location permission is required'); return; }

      const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const lat = loc.coords.latitude;
      const lon = loc.coords.longitude;

      const geocodeRes = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lon });
      let locName = 'Your Location';
      if (geocodeRes && geocodeRes.length > 0) {
        const g = geocodeRes[0];
        locName = [g.city, g.region, g.country].filter(Boolean).join(', ');
      }

      setWeatherLat(lat);
      setWeatherLon(lon);
      setWeatherLocation(locName);
      fetchWeather(lat, lon, locName);
      fetchLocationSoilData(lat, lon, locName);
    } catch (e) {
      Alert.alert('GPS Error', 'Could not get your location. Please try city search instead.');
    } finally {
      setGpsLoading(false);
    }
  };

  // ─── Weather: City Search ───
  const searchCity = async () => {
    if (!cityQuery.trim() || cityQuery.length < 2) return;
    setCitySearching(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/geocode?query=${encodeURIComponent(cityQuery)}`);
      const data = await res.json();
      setCityResults(data.results || []);
    } catch (e) {
      console.log("City search error:", e);
    } finally {
      setCitySearching(false);
    }
  };

  const selectCity = (city) => {
    setWeatherLat(city.latitude);
    setWeatherLon(city.longitude);
    setWeatherLocation(city.display);
    setCityResults([]);
    setCityQuery('');
    fetchWeather(city.latitude, city.longitude, city.display);
    fetchLocationSoilData(city.latitude, city.longitude, city.display);
  };

  // ─── Profile ───
  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/profile`, {
        headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
      });
      const data = await res.json();
      if (data) {
        setFarmerName(data.name || '');
        setFarmerPhone(data.phone || '');
        setFarmerLocation(data.location || '');
      }
    } catch (e) {
      console.log("Profile fetch error:", e);
    }
  };

  // ─── Location Soil Data Auto-Fill ───
  const fetchLocationSoilData = async (lat, lon, locName) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/location-soil-data?lat=${lat}&lon=${lon}&location_name=${encodeURIComponent(locName || '')}`);
      const data = await res.json();
      if (data && data.typical_npk) {
        const npk = data.typical_npk;
        if (selectedSoilType === 'Auto-Detect') {
          if (npk.N) setNVal(String(npk.N));
          if (npk.P) setPVal(String(npk.P));
          if (npk.K) setKVal(String(npk.K));
          if (npk.pH) setPhVal(String(npk.pH));
        }
        setZoneInfo({
          district: data.district || '',
          zone: data.zone || '',
          soil_type: data.soil_type || '',
          source: data.source || '',
          geo_distance_km: data.geo_distance_km,
          avg_rainfall_mm: data.avg_rainfall_mm
        });
      }
    } catch (e) {
      console.log('Location soil data fetch error:', e);
    }
  };

  // ─── Crop Recommendation ───
  const handleRecommend = async () => {
    setRecLoading(true);
    setAiPlanResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/recommend-crop`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          N: parseFloat(nVal) || 0, P: parseFloat(pVal) || 0, K: parseFloat(kVal) || 0,
          ph: parseFloat(phVal) || 0, temperature: parseFloat(tempVal),
          humidity: parseFloat(humVal), rainfall: parseFloat(rainVal),
          soil_type: selectedSoilType,
          location_name: weatherLocation,
          latitude: weatherLat,
          longitude: weatherLon,
          lang: lang
        })
      });
      const data = await res.json();
      setRecommendations(data.recommendations);
      setAiPlanResult(data.ai_agronomic_plan);
    } catch (e) {
      Alert.alert("Error", "Could not connect to backend server.");
    } finally {
      setRecLoading(false);
    }
  };

  // ─── Camera ───
  const openCamera = () => { setCameraVisible(true); };

  const handlePhotoCaptured = async (photoAsset) => {
    setCameraVisible(false);
    const formData = new FormData();
    formData.append('file', { uri: photoAsset.uri, name: 'scan.jpg', type: 'image/jpeg' });
    formData.append('lang', lang);

    setLabelLoading(true);
    setLabelResult(null);
    setScanStep(1);

    const stepTimer = setInterval(() => {
      setScanStep(prev => { if (prev < 3) return prev + 1; clearInterval(stepTimer); return prev; });
    }, 2000);

    try {
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const res = await fetch(`${API_BASE_URL}/api/scan-label`, { method: 'POST', headers, body: formData });
      const data = await res.json();
      clearInterval(stepTimer);
      setScanStep(4);
      setLabelResult(data);
    } catch (e) {
      clearInterval(stepTimer);
      Alert.alert("Error", "Label scan failed.");
    } finally {
      setLabelLoading(false);
    }
  };

  // ─── Text Label Scan ───
  const handleScanText = async () => {
    if (!labelText.trim()) return;
    setLabelLoading(true);
    setLabelResult(null);
    setScanStep(1);

    const stepTimer = setInterval(() => {
      setScanStep(prev => { if (prev < 3) return prev + 1; clearInterval(stepTimer); return prev; });
    }, 1500);

    const formData = new FormData();
    formData.append('text_input', labelText);
    formData.append('lang', lang);

    try {
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const res = await fetch(`${API_BASE_URL}/api/scan-label`, { method: 'POST', headers, body: formData });
      const data = await res.json();
      clearInterval(stepTimer);
      setScanStep(4);
      setLabelResult(data);
    } catch (e) {
      clearInterval(stepTimer);
      Alert.alert("Error", "Product query failed.");
    } finally {
      setLabelLoading(false);
    }
  };

  const scanSteps = [
    '', '📸 Photo uploaded...', '🔍 AI reading brand & product packaging...', '🌐 Matching agronomic database...', '✅ Analysis complete!'
  ];

  const getConfidenceColor = (conf) => {
    if (conf >= 80) return '#22c55e';
    if (conf >= 50) return '#eab308';
    return '#ef4444';
  };

  // ═══════════════════════════════════════════════════
  // ─── AUTH SCREENS (Phone Number Login / Register) ───
  // ═══════════════════════════════════════════════════

  if (checkingAuth) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center', backgroundColor: '#081c15' }]}>
        <Text style={{ fontSize: 48, marginBottom: 16 }}>🌱</Text>
        <ActivityIndicator size="large" color="#52b788" />
        <Text style={{ color: '#52b788', marginTop: 12, fontSize: 16 }}>Loading AgriSense...</Text>
      </View>
    );
  }

  if (!isLoggedIn) {
    return (
      <View style={styles.authContainer}>
        <ScrollView contentContainerStyle={styles.authScroll}>
          <Text style={{ fontSize: 56, textAlign: 'center', marginBottom: 8 }}>🌱</Text>
          <Text style={styles.authBrand}>AgriSense</Text>
          <Text style={styles.authSubtitle}>{t('subtitle', lang)}</Text>

          {/* Language Selector Bar */}
          <View style={{ flexDirection: 'row', justifyContent: 'center', marginVertical: 12 }}>
            {['gu', 'hi', 'en'].map((l) => (
              <TouchableOpacity key={l}
                style={[styles.langBadge, { backgroundColor: lang === l ? '#2d6a4f' : '#e5e7eb', marginHorizontal: 4 }]}
                onPress={() => setLang(l)}>
                <Text style={{ color: lang === l ? '#fff' : '#374151', fontWeight: 'bold', fontSize: 12 }}>
                  {l === 'gu' ? 'ગુજરાતી' : l === 'hi' ? 'हिंदी' : 'English'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <View style={styles.authCard}>
            <Text style={styles.authCardTitle}>{authScreen === 'login' ? t('auth_welcome', lang) : t('auth_create', lang)}</Text>

            <Text style={styles.authLabel}>📱 {t('auth_phone', lang)}</Text>
            <TextInput
              style={styles.authInput}
              value={authPhone}
              onChangeText={setAuthPhone}
              placeholder={t('phone_placeholder', lang)}
              placeholderTextColor="#888"
              keyboardType="phone-pad"
              maxLength={10}
            />

            {authScreen === 'register' && (
              <>
                <Text style={styles.authLabel}>📱 {t('auth_phone_confirm', lang)}</Text>
                <TextInput
                  style={styles.authInput}
                  value={authPhoneConfirm}
                  onChangeText={setAuthPhoneConfirm}
                  placeholder={t('confirm_placeholder', lang)}
                  placeholderTextColor="#888"
                  keyboardType="phone-pad"
                  maxLength={10}
                />
              </>
            )}

            <Text style={styles.authLabel}>🔒 {t('auth_pass', lang)}</Text>
            <TextInput
              style={styles.authInput}
              value={authPassword}
              onChangeText={setAuthPassword}
              placeholder="••••••••"
              placeholderTextColor="#888"
              secureTextEntry
            />

            {authError ? <Text style={styles.authErrorText}>❌ {authError}</Text> : null}

            <TouchableOpacity style={styles.authBtn} onPress={authScreen === 'login' ? handleLogin : handleRegister} disabled={authLoading}>
              {authLoading ? <ActivityIndicator color="#fff" /> :
                <Text style={styles.authBtnText}>{authScreen === 'login' ? t('btn_login', lang) : t('btn_register', lang)}</Text>}
            </TouchableOpacity>

            <TouchableOpacity onPress={() => { setAuthScreen(authScreen === 'login' ? 'register' : 'login'); setAuthError(''); }}>
              <Text style={styles.authSwitchText}>
                {authScreen === 'login' ? t('switch_to_reg', lang) : t('switch_to_login', lang)}
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </View>
    );
  }

  // ═══════════════════════════════════════════════════
  // ─── MAIN APP INTERFACE ───
  // ═══════════════════════════════════════════════════

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Text style={{ fontSize: 24, marginRight: 8 }}>🌱</Text>
          <View>
            <Text style={styles.headerTitle}>{t('app_title', lang)}</Text>
            <Text style={styles.headerSub}>{t('subtitle', lang)}</Text>
          </View>
        </View>

        {/* Language selector */}
        <View style={{ flexDirection: 'row' }}>
          {['gu', 'hi', 'en'].map((l) => (
            <TouchableOpacity key={l}
              style={[styles.langBadge, { backgroundColor: lang === l ? '#52b788' : 'rgba(255,255,255,0.2)' }]}
              onPress={() => setLang(l)}>
              <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 11 }}>
                {l === 'gu' ? 'ગુજરાતી' : l === 'hi' ? 'हिंदी' : 'EN'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* ─── WEATHER TAB ─── */}
        {activeTab === 'weather' && (
          <View>
            {/* Location Selector */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>{t('set_location', lang)}</Text>
              <Text style={{ color: '#1b4332', fontWeight: 'bold', fontSize: 15, marginBottom: 8 }}>
                📍 Current: {weatherLocation}
              </Text>

              <TouchableOpacity style={styles.btnGps} onPress={useGPSLocation} disabled={gpsLoading}>
                {gpsLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>{t('use_gps', lang)}</Text>}
              </TouchableOpacity>

              <Text style={{ fontSize: 12, color: '#666', marginTop: 10, marginBottom: 4 }}>{t('search_city', lang)}</Text>
              <View style={{ flexDirection: 'row' }}>
                <TextInput style={[styles.input, { flex: 1, marginBottom: 0 }]} placeholder="e.g. Surat, Gondal, Deesa"
                  value={cityQuery} onChangeText={setCityQuery} />
                <TouchableOpacity style={styles.btnSearch} onPress={searchCity}>
                  <Text style={{ color: '#fff', fontWeight: 'bold' }}>🔍</Text>
                </TouchableOpacity>
              </View>

              {/* City Results Dropdown */}
              {cityResults.length > 0 && (
                <View style={styles.cityDropdown}>
                  {cityResults.map((city, idx) => (
                    <TouchableOpacity key={idx} style={styles.cityResult} onPress={() => selectCity(city)}>
                      <Text style={{ fontWeight: 'bold', color: '#1b4332' }}>{city.display}</Text>
                      <Text style={{ fontSize: 11, color: '#666' }}>Lat: {city.latitude}, Lon: {city.longitude}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>

            {/* Current Weather Banner */}
            {weather && weather.current && (
              <View style={styles.weatherBanner}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <View>
                    <Text style={{ color: '#fff', fontSize: 36, fontWeight: 'bold' }}>{weather.current.temperature}°C</Text>
                    <Text style={{ color: '#b7e4c7', fontSize: 14 }}>{weather.current.condition}</Text>
                  </View>
                  <Text style={{ fontSize: 48 }}>{weather.current.condition?.includes('Rain') ? '🌧️' : '☀️'}</Text>
                </View>
                <View style={styles.weatherDetailsRow}>
                  <Text style={styles.weatherDetailText}>💧 Humidity: {weather.current.humidity}%</Text>
                  <Text style={styles.weatherDetailText}>💨 Wind: {weather.current.wind_speed} km/h</Text>
                  <Text style={styles.weatherDetailText}>🌧️ Rain: {weather.current.rainfall} mm</Text>
                </View>
              </View>
            )}

            {/* Advisories */}
            {weather && weather.advisories && (
              <View style={styles.card}>
                <Text style={styles.cardTitle}>{t('advisories_title', lang)}</Text>
                {weather.advisories.map((adv, idx) => (
                  <View key={idx} style={styles.advisoryItem}>
                    <Text style={{ fontWeight: 'bold', color: '#854d0e', marginBottom: 2 }}>📢 {adv.title || adv}</Text>
                    {adv.description && <Text style={{ fontSize: 12, color: '#713f12' }}>{adv.description}</Text>}
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* ─── CROP RECOMMEND TAB ─── */}
        {activeTab === 'recommend' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{t('crop_title', lang)}</Text>
            <Text style={styles.cardSub}>4-Layer Context Fusion: Location + Soil Type + NPK Deficits + 3-Month Weather</Text>

            {/* Target Region Badge */}
            <View style={{ backgroundColor: '#eef7f2', padding: 8, borderRadius: 6, marginBottom: 12, flexDirection: 'row', alignItems: 'center' }}>
              <Text style={{ fontSize: 12, color: '#1b4332', fontWeight: 'bold' }}>📍 Target Region: {weatherLocation}</Text>
            </View>

            {/* Soil Type Pills */}
            <Text style={styles.label}>Soil Type & Texture:</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginVertical: 6 }}>
              {[
                { id: 'Auto-Detect', label: '✨ Auto-Detect' },
                { id: 'Black Cotton Soil (કાળી જમીન)', label: '⚫ Black Cotton' },
                { id: 'Sandy Loam Soil (રેતાળ જમીન)', label: '🏖️ Sandy Loam' },
                { id: 'Alluvial Soil (કાંપ જમીન)', label: '🏞️ Alluvial' },
                { id: 'Red Clay Soil (લાલ જમીન)', label: '🔴 Red Clay' }
              ].map((st) => (
                <TouchableOpacity key={st.id}
                  style={[styles.methodBadge, { marginRight: 6, backgroundColor: selectedSoilType === st.id ? '#1b4332' : '#e5e7eb' }]}
                  onPress={() => setSelectedSoilType(st.id)}>
                  <Text style={{ color: selectedSoilType === st.id ? '#fff' : '#374151', fontSize: 11, fontWeight: 'bold' }}>
                    {st.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <Text style={styles.label}>Nitrogen (N) kg/ha</Text>
            <TextInput style={styles.input} value={nVal} onChangeText={setNVal} keyboardType="numeric" placeholder="Auto-filled from zone" />
            <Text style={styles.label}>Phosphorus (P) kg/ha</Text>
            <TextInput style={styles.input} value={pVal} onChangeText={setPVal} keyboardType="numeric" placeholder="Auto-filled from zone" />
            <Text style={styles.label}>Potassium (K) kg/ha</Text>
            <TextInput style={styles.input} value={kVal} onChangeText={setKVal} keyboardType="numeric" placeholder="Auto-filled from zone" />
            <Text style={styles.label}>Soil pH Level</Text>
            <TextInput style={styles.input} value={phVal} onChangeText={setPhVal} keyboardType="numeric" placeholder="Auto-filled from zone" />

            {/* Zone Info Badge */}
            {zoneInfo && zoneInfo.district ? (
              <View style={{ backgroundColor: '#ecfdf5', borderWidth: 1, borderColor: '#6ee7b7', padding: 10, borderRadius: 8, marginBottom: 12 }}>
                <Text style={{ fontSize: 11, color: '#065f46', fontWeight: 'bold' }}>📍 Auto-filled from {zoneInfo.district} District zone data</Text>
                <Text style={{ fontSize: 10, color: '#047857', marginTop: 2 }}>Zone: {zoneInfo.zone} | Soil: {zoneInfo.soil_type}{zoneInfo.geo_distance_km ? ` | ~${zoneInfo.geo_distance_km}km to center` : ''}</Text>
                <Text style={{ fontSize: 9, color: '#6b7280', marginTop: 2 }}>ℹ️ NPK & pH values are zone baselines — override with your soil test report if available</Text>
              </View>
            ) : null}

            <TouchableOpacity style={styles.btnPrimary} onPress={handleRecommend}>
              {recLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>{t('predict_btn', lang)}</Text>}
            </TouchableOpacity>

            {/* AI Agronomic Plan Result Card */}
            {aiPlanResult && (
              <View style={{ marginTop: 16 }}>
                <View style={{ backgroundColor: '#7c3aed', padding: 10, borderRadius: 8, marginBottom: 12 }}>
                  <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 14 }}>
                    🤖 Geographical AI Agronomic Action Plan
                  </Text>
                  <Text style={{ color: '#e9d5ff', fontSize: 11, marginTop: 2 }}>
                    Zone: {aiPlanResult.agro_climatic_zone || 'Middle Gujarat Zone'} | Soil: {aiPlanResult.detected_soil_type}
                  </Text>
                </View>

                {/* Recommended Crops */}
                <Text style={{ fontWeight: 'bold', fontSize: 14, color: '#1b4332', marginBottom: 8 }}>🌾 Recommended Crops & Varieties:</Text>
                {aiPlanResult.recommended_crops?.map((crop, idx) => (
                  <View key={idx} style={styles.recBox}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text style={styles.recName}>{idx + 1}. {crop.crop_name}</Text>
                      <View style={[styles.methodBadge, { backgroundColor: '#1b4332' }]}>
                        <Text style={{ color: '#fff', fontSize: 10, fontWeight: 'bold' }}>{crop.suitability_score}% Match</Text>
                      </View>
                    </View>
                    {crop.recommended_variety && (
                      <Text style={{ fontSize: 12, fontWeight: 'bold', color: '#2563eb', marginTop: 2 }}>
                        🌱 Variety: {crop.recommended_variety}
                      </Text>
                    )}
                    <Text style={styles.recTips}>💡 {crop.suitability_reason}</Text>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 }}>
                      <Text style={{ fontSize: 11, color: '#4b5563' }}>⏱️ Duration: {crop.season_duration}</Text>
                      <Text style={{ fontSize: 11, color: '#059669', fontWeight: 'bold' }}>📈 Yield: {crop.expected_yield_per_acre}</Text>
                    </View>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* ─── LABEL SCANNER TAB ─── */}
        {activeTab === 'scan' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{t('scanner_title', lang)}</Text>
            <Text style={styles.cardSub}>{t('scanner_sub', lang)}</Text>

            <TouchableOpacity style={styles.cameraDropzone} onPress={openCamera}>
              <Text style={{ fontSize: 36 }}>📷</Text>
              <Text style={{ fontWeight: 'bold', color: '#1b4332', marginTop: 4 }}>{t('take_photo', lang)}</Text>
              <Text style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{t('capture_sub', lang)}</Text>
            </TouchableOpacity>

            <TextInput style={styles.input} placeholder={t('type_product', lang)}
              value={labelText} onChangeText={setLabelText} />
            <TouchableOpacity style={styles.btnPrimary} onPress={handleScanText}>
              <Text style={styles.btnText}>{t('analyze_btn', lang)}</Text>
            </TouchableOpacity>

            {/* Animated Scan Progress */}
            {labelLoading && scanStep > 0 && (
              <View style={styles.scanProgress}>
                <ActivityIndicator color="#1b4332" size="small" />
                <Text style={styles.scanStepText}>{scanSteps[scanStep]}</Text>
              </View>
            )}

            {/* Label Scan Result Card */}
            {labelResult && (
              <View style={styles.resultCard}>
                {labelResult.matched_product ? (
                  <View>
                    <View style={styles.resultHeader}>
                      <Text style={styles.resultTitle}>
                        📦 {labelResult.matched_product.name}
                      </Text>
                      <View style={[styles.confidenceBadge, { backgroundColor: getConfidenceColor(labelResult.match_confidence) }]}>
                        <Text style={styles.confidenceText}>{labelResult.match_confidence}% Match</Text>
                      </View>
                    </View>

                    <Text style={styles.label}>{t('brand', lang)}:</Text>
                    <Text style={styles.valueText}>{labelResult.matched_product.brand || 'N/A'}</Text>

                    <Text style={styles.label}>{t('active', lang)}:</Text>
                    <Text style={styles.valueText}>{labelResult.matched_product.active_ingredient}</Text>

                    <Text style={styles.label}>{t('dosage', lang)}:</Text>
                    <Text style={styles.valueText}>{labelResult.matched_product.recommended_dosage}</Text>

                    <Text style={styles.label}>🎯 Target Crops & Pests:</Text>
                    <Text style={styles.valueText}>
                      {Array.isArray(labelResult.matched_product.target_pests) ? labelResult.matched_product.target_pests.join(', ') : labelResult.matched_product.target_pests}
                    </Text>

                    <Text style={styles.label}>⚠️ Safety & Precaution:</Text>
                    <Text style={styles.valueText}>{labelResult.matched_product.safety_precaution || 'Wear gloves, mask, and store away from children.'}</Text>
                  </View>
                ) : (
                  <View style={{ padding: 12 }}>
                    <Text style={{ fontWeight: 'bold', color: '#1b4332', fontSize: 14 }}>🔍 Product Identification Result:</Text>
                    <Text style={{ fontSize: 13, color: '#374151', marginVertical: 6 }}>{labelResult.ai_summary}</Text>
                    {labelResult.disclaimer ? (
                      <Text style={{ fontSize: 11, color: '#b91c1c', marginTop: 4 }}>{labelResult.disclaimer}</Text>
                    ) : null}
                  </View>
                )}
              </View>
            )}
          </View>
        )}

        {/* ─── PROFILE TAB ─── */}
        {activeTab === 'profile' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{t('profile_title', lang)}</Text>
            {currentUser && (
              <View style={{ backgroundColor: '#f0fdf4', padding: 10, borderRadius: 8, marginBottom: 14 }}>
                <Text style={{ fontWeight: 'bold', color: '#166534' }}>📱 Logged in Phone: {currentUser.username}</Text>
              </View>
            )}

            <Text style={styles.label}>Farmer Name</Text>
            <TextInput style={styles.input} value={farmerName} onChangeText={setFarmerName} placeholder="Enter your name" />

            <Text style={styles.label}>Mobile Number</Text>
            <TextInput style={styles.input} value={farmerPhone} onChangeText={setFarmerPhone} keyboardType="phone-pad" placeholder="Enter mobile number" />

            <Text style={styles.label}>Village / District</Text>
            <TextInput style={styles.input} value={farmerLocation} onChangeText={setFarmerLocation} placeholder="e.g. Gondal, Rajkot" />

            <TouchableOpacity style={styles.btnPrimary} onPress={() => Alert.alert('Saved', 'Profile updated successfully!')}>
              <Text style={styles.btnText}>{t('save_profile', lang)}</Text>
            </TouchableOpacity>

            <TouchableOpacity style={[styles.btnPrimary, { backgroundColor: '#ef4444', marginTop: 14 }]} onPress={handleLogout}>
              <Text style={styles.btnText}>🚪 Logout</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* ─── BOTTOM NAVIGATION BAR (4 TABS) ─── */}
      <View style={styles.bottomBar}>
        {['weather', 'recommend', 'scan', 'profile'].map((tab) => (
          <TouchableOpacity key={tab} style={styles.tabItem} onPress={() => setActiveTab(tab)}>
            <Text style={{ fontSize: 20 }}>
              {tab === 'weather' ? '🌤️' : tab === 'recommend' ? '🌱' : tab === 'scan' ? '🏷️' : '👨‍🌾'}
            </Text>
            <Text style={[styles.tabLabel, { color: activeTab === tab ? '#52b788' : '#9ca3af' }]}>
              {t(`tab_${tab}`, lang)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* ─── CAMERA SCANNER MODAL ─── */}
      {cameraVisible && (
        <Modal visible animationType="slide">
          <CameraScanner
            onPhotoCaptured={handlePhotoCaptured}
            onClose={() => setCameraVisible(false)}
            modeTitle="Scan Product Label"
          />
        </Modal>
      )}
    </View>
  );
}

// ─── STYLES ───
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f3f4f6' },
  header: { backgroundColor: '#081c15', padding: 16, paddingTop: Platform.OS === 'ios' ? 44 : 32, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  headerSub: { color: '#52b788', fontSize: 11 },
  langBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12, marginLeft: 4 },
  scrollContent: { padding: 14, paddingBottom: 80 },
  card: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 14, elevation: 2, boxShadow: '0px 1px 3px rgba(0,0,0,0.1)' },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#1b4332', marginBottom: 4 },
  cardSub: { fontSize: 11, color: '#6b7280', marginBottom: 12 },
  label: { fontSize: 12, color: '#374151', fontWeight: 'bold', marginTop: 8, marginBottom: 2 },
  valueText: { fontSize: 13, color: '#1b4332', marginBottom: 6 },
  input: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 10, fontSize: 14, marginBottom: 10, backgroundColor: '#f9fafb' },
  btnPrimary: { backgroundColor: '#2d6a4f', padding: 12, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  btnGps: { backgroundColor: '#1b4332', padding: 10, borderRadius: 8, alignItems: 'center', marginVertical: 6 },
  btnSearch: { backgroundColor: '#2d6a4f', width: 44, justifyContent: 'center', alignItems: 'center', borderRadius: 8, marginLeft: 6 },
  cityDropdown: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, marginTop: 4, maxHeight: 150 },
  cityResult: { padding: 10, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  weatherBanner: { backgroundColor: '#1b4332', padding: 16, borderRadius: 12, marginBottom: 14 },
  weatherDetailsRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.2)' },
  weatherDetailText: { color: '#e5e7eb', fontSize: 11 },
  advisoryItem: { backgroundColor: '#fef9c3', padding: 10, borderRadius: 8, marginTop: 6 },
  cameraDropzone: { borderStyle: 'dashed', borderWidth: 2, borderColor: '#52b788', borderRadius: 12, padding: 20, alignItems: 'center', backgroundColor: '#f0fdf4', marginBottom: 12 },
  scanProgress: { backgroundColor: '#ecfdf5', padding: 12, borderRadius: 8, flexDirection: 'row', alignItems: 'center', marginTop: 10 },
  scanStepText: { marginLeft: 10, color: '#065f46', fontSize: 12, fontWeight: 'bold' },
  resultCard: { backgroundColor: '#f8fafc', borderLeftWidth: 4, borderLeftColor: '#2d6a4f', padding: 14, borderRadius: 8, marginTop: 14 },
  resultHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  resultTitle: { fontSize: 16, fontWeight: 'bold', color: '#0f172a', flex: 1 },
  confidenceBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 12 },
  confidenceText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  methodBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  recBox: { backgroundColor: '#f8fafc', padding: 12, borderRadius: 8, marginBottom: 8, borderLeftWidth: 3, borderLeftColor: '#2563eb' },
  recName: { fontWeight: 'bold', fontSize: 14, color: '#1e293b' },
  recTips: { fontSize: 11, color: '#475569', marginTop: 4 },
  bottomBar: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 60, backgroundColor: '#081c15', flexDirection: 'row', borderTopWidth: 1, borderTopColor: '#1b4332' },
  tabItem: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  tabLabel: { fontSize: 10, fontWeight: 'bold', marginTop: 2 },
  authContainer: { flex: 1, backgroundColor: '#081c15' },
  authScroll: { flexGrow: 1, justifyContent: 'center', padding: 20 },
  authBrand: { fontSize: 32, fontWeight: 'bold', color: '#fff', textAlign: 'center' },
  authSubtitle: { fontSize: 13, color: '#52b788', textAlign: 'center', marginBottom: 20 },
  authCard: { backgroundColor: '#fff', padding: 20, borderRadius: 16, elevation: 4 },
  authCardTitle: { fontSize: 18, fontWeight: 'bold', color: '#1b4332', marginBottom: 16, textAlign: 'center' },
  authLabel: { fontSize: 12, fontWeight: 'bold', color: '#374151', marginBottom: 4, marginTop: 8 },
  authInput: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 12, fontSize: 14, backgroundColor: '#f9fafb' },
  authBtn: { backgroundColor: '#2d6a4f', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 16 },
  authBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  authErrorText: { color: '#dc2626', fontSize: 12, marginTop: 8, textAlign: 'center', fontWeight: 'bold' },
  authSwitchText: { color: '#2d6a4f', fontSize: 13, textAlign: 'center', marginTop: 16, fontWeight: 'bold' }
});
