import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, TextInput, Modal, ActivityIndicator, Alert, Animated, Dimensions } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import CameraScanner from './components/CameraScanner';

// Auto-detected Mobile Hotspot IP address
const API_BASE_URL = 'http://10.160.70.72:8000';

export default function App() {
  // ─── Auth State ───
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authToken, setAuthToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [authScreen, setAuthScreen] = useState('login'); // 'login' or 'register'
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authConfirm, setAuthConfirm] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');
  const [checkingAuth, setCheckingAuth] = useState(true);

  // ─── App State ───
  const [activeTab, setActiveTab] = useState('weather');
  const [lang, setLang] = useState('en');

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
  const [nVal, setNVal] = useState('80');
  const [pVal, setPVal] = useState('45');
  const [kVal, setKVal] = useState('50');
  const [phVal, setPhVal] = useState('6.5');
  const [tempVal, setTempVal] = useState('26');
  const [humVal, setHumVal] = useState('75');
  const [rainVal, setRainVal] = useState('110');
  const [recommendations, setRecommendations] = useState(null);
  const [recLoading, setRecLoading] = useState(false);

  // ─── Soil Health OCR State ───
  const [soilParsed, setSoilParsed] = useState(null);
  const [soilLoading, setSoilLoading] = useState(false);

  // ─── Label Scanner State ───
  const [labelText, setLabelText] = useState('');
  const [labelResult, setLabelResult] = useState(null);
  const [labelLoading, setLabelLoading] = useState(false);
  const [scanStep, setScanStep] = useState(0);

  // ─── Camera Modal State ───
  const [cameraVisible, setCameraVisible] = useState(false);
  const [cameraMode, setCameraMode] = useState('label');

  // ─── Farmer Profile State ───
  const [farmerName, setFarmerName] = useState('');
  const [farmerPhone, setFarmerPhone] = useState('');
  const [farmerLocation, setFarmerLocation] = useState('');
  const [profileSaving, setProfileSaving] = useState(false);

  // ─── Animations ───
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // ─── Auth Headers ───
  const authHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    return headers;
  };

  // ─── On App Launch: Check for saved token ───
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
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
    }
  }, [isLoggedIn, authToken]);

  // ─── Auth: Register ───
  const handleRegister = async () => {
    setAuthError('');
    if (authPassword !== authConfirm) { setAuthError('Passwords do not match'); return; }
    if (authUsername.length < 3) { setAuthError('Username must be at least 3 characters'); return; }
    if (authPassword.length < 4) { setAuthError('Password must be at least 4 characters'); return; }

    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername.trim(), password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) { setAuthError(data.detail || 'Registration failed'); return; }

      await AsyncStorage.setItem('agrisense_token', data.token);
      await AsyncStorage.setItem('agrisense_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
      setAuthToken(data.token);
      setCurrentUser({ user_id: data.user_id, username: data.username });
      setIsLoggedIn(true);
    } catch (e) {
      setAuthError('Could not connect to server. Is the backend running?');
    } finally {
      setAuthLoading(false);
    }
  };

  // ─── Auth: Login ───
  const handleLogin = async () => {
    setAuthError('');
    if (!authUsername.trim() || !authPassword) { setAuthError('Enter username and password'); return; }

    setAuthLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername.trim(), password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) { setAuthError(data.detail || 'Login failed'); return; }

      await AsyncStorage.setItem('agrisense_token', data.token);
      await AsyncStorage.setItem('agrisense_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
      setAuthToken(data.token);
      setCurrentUser({ user_id: data.user_id, username: data.username });
      setIsLoggedIn(true);
    } catch (e) {
      setAuthError('Could not connect to server. Is the backend running?');
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
    setAuthUsername('');
    setAuthPassword('');
    setAuthConfirm('');
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

      // Reverse geocode to get city name
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
    } catch (e) { console.log("Profile fetch error:", e); }
  };

  const saveProfile = async () => {
    setProfileSaving(true);
    try {
      await fetch(`${API_BASE_URL}/api/profile`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ id: 1, name: farmerName, phone: farmerPhone, location: farmerLocation,
          latitude: weatherLat, longitude: weatherLon, soil_type: 'Loamy Soil',
          N: 180, P: 42, K: 160, pH: 7.2, EC: 0.65, OC: 0.52, preferred_language: lang })
      });
      Alert.alert('✅ Saved', 'Profile updated successfully!');
    } catch (e) {
      Alert.alert('Error', 'Could not save profile.');
    } finally {
      setProfileSaving(false);
    }
  };

  // ─── Crop Recommendation ───
  const handleRecommend = async () => {
    setRecLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/recommend-crop`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ N: parseFloat(nVal), P: parseFloat(pVal), K: parseFloat(kVal),
          ph: parseFloat(phVal), temperature: parseFloat(tempVal),
          humidity: parseFloat(humVal), rainfall: parseFloat(rainVal) })
      });
      const data = await res.json();
      setRecommendations(data.recommendations);
    } catch (e) {
      Alert.alert("Error", "Could not connect to backend server.");
    } finally {
      setRecLoading(false);
    }
  };

  // ─── Camera ───
  const openCameraFor = (mode) => { setCameraMode(mode); setCameraVisible(true); };

  const handlePhotoCaptured = async (photoAsset) => {
    setCameraVisible(false);
    const formData = new FormData();
    formData.append('file', { uri: photoAsset.uri, name: 'scan.jpg', type: 'image/jpeg' });
    formData.append('lang', lang);

    if (cameraMode === 'label') {
      setLabelLoading(true);
      setLabelResult(null);
      setScanStep(1);

      // Animate through scan steps
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
    } else {
      setSoilLoading(true);
      try {
        const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
        const res = await fetch(`${API_BASE_URL}/api/parse-soil-card`, { method: 'POST', headers, body: formData });
        const data = await res.json();
        setSoilParsed(data);
      } catch (e) {
        Alert.alert("Error", "Soil card scan failed.");
      } finally {
        setSoilLoading(false);
      }
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

  // ─── Scan Step Labels ───
  const scanSteps = [
    '', '📸 Uploading photo...', '🔍 AI analyzing image...', '🌐 Searching product database...', '✅ Analysis complete!'
  ];

  // ─── Confidence Bar Color ───
  const getConfidenceColor = (conf) => {
    if (conf >= 80) return '#22c55e';
    if (conf >= 50) return '#eab308';
    return '#ef4444';
  };

  // ═══════════════════════════════════════════════════
  // ─── AUTH SCREENS (Login / Register) ───
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
          <Text style={styles.authSubtitle}>AI-Powered Agricultural Assistant</Text>

          <View style={styles.authCard}>
            <Text style={styles.authCardTitle}>{authScreen === 'login' ? 'Welcome Back' : 'Create Account'}</Text>

            <Text style={styles.authLabel}>Username</Text>
            <TextInput style={styles.authInput} value={authUsername} onChangeText={setAuthUsername}
              placeholder="Enter username" placeholderTextColor="#666" autoCapitalize="none" />

            <Text style={styles.authLabel}>Password</Text>
            <TextInput style={styles.authInput} value={authPassword} onChangeText={setAuthPassword}
              placeholder="Enter password" placeholderTextColor="#666" secureTextEntry />

            {authScreen === 'register' && (
              <>
                <Text style={styles.authLabel}>Confirm Password</Text>
                <TextInput style={styles.authInput} value={authConfirm} onChangeText={setAuthConfirm}
                  placeholder="Confirm password" placeholderTextColor="#666" secureTextEntry />
              </>
            )}

            {authError ? <Text style={styles.authErrorText}>❌ {authError}</Text> : null}

            <TouchableOpacity style={styles.authBtn} onPress={authScreen === 'login' ? handleLogin : handleRegister} disabled={authLoading}>
              {authLoading ? <ActivityIndicator color="#fff" /> :
                <Text style={styles.authBtnText}>{authScreen === 'login' ? '🔓 Login' : '📝 Create Account'}</Text>}
            </TouchableOpacity>

            <TouchableOpacity onPress={() => { setAuthScreen(authScreen === 'login' ? 'register' : 'login'); setAuthError(''); }}>
              <Text style={styles.authSwitchText}>
                {authScreen === 'login' ? "Don't have an account? Register" : "Already have an account? Login"}
              </Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </View>
    );
  }

  // ═══════════════════════════════════════════════════
  // ─── MAIN APP (after login) ───
  // ═══════════════════════════════════════════════════

  return (
    <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Text style={{ fontSize: 24, marginRight: 8 }}>🌱</Text>
          <View>
            <Text style={styles.brandTitle}>AgriSense</Text>
            <Text style={styles.brandSub}>👤 {currentUser?.username}</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.langBadge} onPress={() => setLang(lang === 'en' ? 'gu' : (lang === 'gu' ? 'hi' : 'en'))}>
          <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 12 }}>{lang.toUpperCase()}</Text>
        </TouchableOpacity>
      </View>

      {/* Main Content */}
      <ScrollView style={styles.content} keyboardShouldPersistTaps="handled">

        {/* ─── WEATHER TAB ─── */}
        {activeTab === 'weather' && (
          <View>
            {/* GPS & City Search */}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>📍 Set Location</Text>
              <TouchableOpacity style={[styles.btnPrimary, { backgroundColor: '#2563eb' }]} onPress={useGPSLocation} disabled={gpsLoading}>
                {gpsLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>📍 Use My GPS Location</Text>}
              </TouchableOpacity>

              <Text style={[styles.label, { marginTop: 12 }]}>Or search a city:</Text>
              <View style={{ flexDirection: 'row', gap: 8, marginTop: 4 }}>
                <TextInput style={[styles.input, { flex: 1 }]} value={cityQuery} onChangeText={setCityQuery}
                  placeholder="e.g. Mumbai, Ahmedabad..." onSubmitEditing={searchCity} />
                <TouchableOpacity style={[styles.btnPrimary, { marginTop: 0, paddingHorizontal: 16 }]} onPress={searchCity}>
                  {citySearching ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.btnText}>🔍</Text>}
                </TouchableOpacity>
              </View>

              {cityResults.length > 0 && (
                <View style={{ marginTop: 8 }}>
                  {cityResults.map((city, idx) => (
                    <TouchableOpacity key={idx} style={styles.cityResult} onPress={() => selectCity(city)}>
                      <Text style={{ fontWeight: 'bold', color: '#1b4332' }}>📍 {city.display}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>

            {/* Weather Display */}
            <View style={styles.weatherHero}>
              <Text style={styles.locationText}>📍 {weather?.location || weatherLocation}</Text>
              <Text style={styles.tempText}>{weather?.current?.temperature?.toFixed(1) || '--'}°C</Text>
              <Text style={styles.descText}>{weather?.current?.icon} {weather?.current?.description || 'Loading...'}</Text>
              <View style={{ flexDirection: 'row', justifyContent: 'space-around', width: '100%', marginTop: 12 }}>
                <Text style={{ color: '#d8f3dc', fontSize: 12 }}>💧 {weather?.current?.humidity || '--'}%</Text>
                <Text style={{ color: '#d8f3dc', fontSize: 12 }}>💨 {weather?.current?.wind_speed || '--'} km/h</Text>
                <Text style={{ color: '#d8f3dc', fontSize: 12 }}>🌧️ {weather?.current?.precipitation || '0'} mm</Text>
              </View>
            </View>

            <View style={styles.card}>
              <Text style={styles.cardTitle}>Agricultural Advisories</Text>
              {weather?.advisories?.map((adv, idx) => (
                <View key={idx} style={styles.advisoryBox}>
                  <Text style={styles.advTitle}>{adv[`title_${lang}`] || adv.title}</Text>
                  <Text style={styles.advMsg}>{adv[`message_${lang}`] || adv.message}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* ─── CROP RECOMMEND TAB ─── */}
        {activeTab === 'recommend' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>🌱 AI Crop Recommender</Text>
            <Text style={styles.cardSub}>Random Forest ML model trained on 2,200 soil-climate profiles</Text>
            <Text style={styles.label}>Nitrogen (N) kg/ha</Text>
            <TextInput style={styles.input} value={nVal} onChangeText={setNVal} keyboardType="numeric" />
            <Text style={styles.label}>Phosphorus (P) kg/ha</Text>
            <TextInput style={styles.input} value={pVal} onChangeText={setPVal} keyboardType="numeric" />
            <Text style={styles.label}>Potassium (K) kg/ha</Text>
            <TextInput style={styles.input} value={kVal} onChangeText={setKVal} keyboardType="numeric" />
            <Text style={styles.label}>Soil pH Level</Text>
            <TextInput style={styles.input} value={phVal} onChangeText={setPhVal} keyboardType="numeric" />

            <TouchableOpacity style={styles.btnPrimary} onPress={handleRecommend}>
              {recLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>🌱 Predict Suitable Crops</Text>}
            </TouchableOpacity>

            {recommendations && recommendations.map((rec, i) => (
              <View key={i} style={styles.recBox}>
                <Text style={styles.recName}>{i+1}. {rec.name} ({rec.confidence}% Match)</Text>
                <Text style={styles.recTips}>💡 {rec.tips}</Text>
              </View>
            ))}
          </View>
        )}

        {/* ─── SOIL TAB ─── */}
        {activeTab === 'soil' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>📄 Soil Health Card Reader</Text>
            <TouchableOpacity style={styles.cameraDropzone} onPress={() => openCameraFor('soil')}>
              <Text style={{ fontSize: 32 }}>📸</Text>
              <Text style={{ fontWeight: 'bold', color: '#1b4332', marginTop: 4 }}>Capture Soil Health Card</Text>
            </TouchableOpacity>
            {soilLoading && <ActivityIndicator size="large" color="#1b4332" />}
            {soilParsed && (
              <View style={{ marginTop: 14 }}>
                <Text style={styles.cardTitle}>Extracted Parameters</Text>
                <Text style={styles.label}>Nitrogen (N): {soilParsed.parameters?.N} kg/ha</Text>
                <Text style={styles.label}>Phosphorus (P): {soilParsed.parameters?.P} kg/ha</Text>
                <Text style={styles.label}>Potassium (K): {soilParsed.parameters?.K} kg/ha</Text>
                <Text style={styles.label}>Soil pH: {soilParsed.parameters?.pH}</Text>
              </View>
            )}
          </View>
        )}

        {/* ─── LABEL SCANNER TAB ─── */}
        {activeTab === 'scan' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>🏷️ AI Label Scanner</Text>
            <Text style={styles.cardSub}>Powered by Gemini Vision AI — Take a photo of any pesticide, fertilizer, or herbicide</Text>

            <TouchableOpacity style={styles.cameraDropzone} onPress={() => openCameraFor('label')}>
              <Text style={{ fontSize: 36 }}>📷</Text>
              <Text style={{ fontWeight: 'bold', color: '#1b4332', marginTop: 4 }}>Take Photo of Product</Text>
              <Text style={{ fontSize: 11, color: '#666', marginTop: 2 }}>Capture the label, bag, or bottle</Text>
            </TouchableOpacity>

            <TextInput style={styles.input} placeholder="Or type product name (e.g. Urea, Chlorpyrifos)"
              value={labelText} onChangeText={setLabelText} />
            <TouchableOpacity style={styles.btnPrimary} onPress={handleScanText}>
              <Text style={styles.btnText}>🔍 Analyze Product</Text>
            </TouchableOpacity>

            {/* Animated Scan Progress */}
            {labelLoading && scanStep > 0 && (
              <View style={styles.scanProgress}>
                {[1, 2, 3].map(step => (
                  <View key={step} style={[styles.scanStepRow, scanStep >= step && styles.scanStepActive]}>
                    {scanStep === step ? <ActivityIndicator size="small" color="#1b4332" /> :
                      scanStep > step ? <Text style={{ fontSize: 16 }}>✅</Text> : <Text style={{ fontSize: 16 }}>⏳</Text>}
                    <Text style={[styles.scanStepText, scanStep >= step && { color: '#1b4332', fontWeight: 'bold' }]}>
                      {scanSteps[step]}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Results */}
            {labelResult && (
              <View style={styles.summaryBox}>
                {/* Analysis Method Badge */}
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <View style={[styles.methodBadge, { backgroundColor: labelResult.analysis_method === 'gemini_vision' ? '#7c3aed' : '#6b7280' }]}>
                    <Text style={{ color: '#fff', fontSize: 10, fontWeight: 'bold' }}>
                      {labelResult.analysis_method === 'gemini_vision' ? '🤖 Gemini Vision' : '📝 Text Match'}
                    </Text>
                  </View>
                </View>

                {/* Confidence Bar */}
                <View style={{ marginBottom: 10 }}>
                  <Text style={{ fontSize: 12, fontWeight: 'bold', color: '#333' }}>Confidence: {labelResult.match_confidence}%</Text>
                  <View style={styles.confBarBg}>
                    <View style={[styles.confBarFill, { width: `${Math.min(labelResult.match_confidence, 100)}%`, backgroundColor: getConfidenceColor(labelResult.match_confidence) }]} />
                  </View>
                </View>

                <Text style={styles.recName}>🏷️ {labelResult.matched_product?.name}</Text>
                {labelResult.matched_product?.brand && <Text style={{ marginTop: 2, color: '#666' }}>🏭 {labelResult.matched_product.brand}</Text>}
                <Text style={{ marginTop: 4 }}>🧪 Active: {labelResult.matched_product?.active_ingredient}</Text>
                <Text style={{ marginTop: 4 }}>💧 Dosage: {labelResult.matched_product?.dosage}</Text>
                {labelResult.matched_product?.target_pests?.length > 0 && (
                  <Text style={{ marginTop: 4 }}>🐛 Targets: {Array.isArray(labelResult.matched_product.target_pests) ? labelResult.matched_product.target_pests.join(', ') : labelResult.matched_product.target_pests}</Text>
                )}
                <Text style={{ marginTop: 10, fontStyle: 'italic', fontSize: 13, lineHeight: 18 }}>🤖 {labelResult.ai_summary}</Text>
                <Text style={{ marginTop: 8, fontSize: 11, color: '#666' }}>{labelResult.disclaimer}</Text>
              </View>
            )}
          </View>
        )}

        {/* ─── PROFILE TAB ─── */}
        {activeTab === 'profile' && (
          <View>
            <View style={styles.card}>
              <View style={{ alignItems: 'center', marginBottom: 16 }}>
                <View style={styles.avatarCircle}>
                  <Text style={{ fontSize: 36 }}>👤</Text>
                </View>
                <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#1b4332', marginTop: 8 }}>{currentUser?.username}</Text>
                <Text style={{ fontSize: 12, color: '#666' }}>Logged in</Text>
              </View>

              <Text style={styles.cardTitle}>Edit Profile</Text>
              <Text style={styles.label}>Full Name</Text>
              <TextInput style={styles.input} value={farmerName} onChangeText={setFarmerName} placeholder="Enter your full name" />
              <Text style={styles.label}>Phone Number</Text>
              <TextInput style={styles.input} value={farmerPhone} onChangeText={setFarmerPhone} placeholder="+91 XXXXX XXXXX" keyboardType="phone-pad" />
              <Text style={styles.label}>Location / Village</Text>
              <TextInput style={styles.input} value={farmerLocation} onChangeText={setFarmerLocation} placeholder="e.g. Anand, Gujarat" />

              <TouchableOpacity style={styles.btnPrimary} onPress={saveProfile}>
                {profileSaving ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>💾 Save Profile</Text>}
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
              <Text style={styles.logoutBtnText}>🚪 Logout</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Bottom Nav */}
      <View style={styles.navBar}>
        {['weather', 'recommend', 'soil', 'scan', 'profile'].map((tab) => (
          <TouchableOpacity key={tab} style={styles.navItem} onPress={() => setActiveTab(tab)}>
            <Text style={{ fontSize: 20 }}>
              {tab === 'weather' ? '🌤️' : tab === 'recommend' ? '🌱' : tab === 'soil' ? '📄' : tab === 'scan' ? '🏷️' : '👤'}
            </Text>
            <Text style={{ fontSize: 10, color: activeTab === tab ? '#1b4332' : '#999', fontWeight: activeTab === tab ? 'bold' : 'normal' }}>
              {tab.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Camera Modal */}
      <Modal visible={cameraVisible} animationType="slide">
        <CameraScanner
          modeTitle={cameraMode === 'label' ? "Scan Product Label" : "Scan Soil Health Card"}
          onPhotoCaptured={handlePhotoCaptured}
          onClose={() => setCameraVisible(false)}
        />
      </Modal>
    </Animated.View>
  );
}

// ═══════════════════════════════════════════════════
// ─── STYLES ───
// ═══════════════════════════════════════════════════

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f8f5' },

  // Auth Screens
  authContainer: { flex: 1, backgroundColor: '#081c15' },
  authScroll: { flexGrow: 1, justifyContent: 'center', padding: 24, paddingTop: 60 },
  authBrand: { fontSize: 32, fontWeight: 'bold', color: '#fff', textAlign: 'center' },
  authSubtitle: { fontSize: 14, color: '#52b788', textAlign: 'center', marginBottom: 30 },
  authCard: { backgroundColor: '#fff', borderRadius: 20, padding: 24, elevation: 4 },
  authCardTitle: { fontSize: 20, fontWeight: 'bold', color: '#1b4332', marginBottom: 16, textAlign: 'center' },
  authLabel: { fontSize: 13, fontWeight: 'bold', color: '#333', marginTop: 12 },
  authInput: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 10, padding: 12, marginTop: 4, backgroundColor: '#f9fafb', fontSize: 15 },
  authErrorText: { color: '#ef4444', fontSize: 13, marginTop: 10, textAlign: 'center' },
  authBtn: { backgroundColor: '#1b4332', padding: 16, borderRadius: 12, alignItems: 'center', marginTop: 20 },
  authBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  authSwitchText: { color: '#2563eb', textAlign: 'center', marginTop: 16, fontSize: 14 },

  // Header
  header: { paddingTop: 45, paddingBottom: 15, paddingHorizontal: 20, backgroundColor: '#1b4332', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  brandTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  brandSub: { color: '#52b788', fontSize: 11 },
  langBadge: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },

  // Content
  content: { flex: 1, padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16, elevation: 2 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#1b4332', marginBottom: 6 },
  cardSub: { fontSize: 12, color: '#666', marginBottom: 12 },

  // Weather
  weatherHero: { backgroundColor: '#2d6a4f', borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 16 },
  locationText: { color: '#d8f3dc', fontSize: 14, fontWeight: 'bold' },
  tempText: { color: '#fff', fontSize: 44, fontWeight: 'bold', marginVertical: 4 },
  descText: { color: '#fff', fontSize: 14 },
  advisoryBox: { backgroundColor: '#fffbe6', borderLeftWidth: 4, borderLeftColor: '#f59e0b', padding: 10, borderRadius: 6, marginVertical: 4 },
  advTitle: { fontWeight: 'bold', fontSize: 13, color: '#b45309' },
  advMsg: { fontSize: 12, color: '#374151', marginTop: 2 },

  // City Search
  cityResult: { backgroundColor: '#f0fdf4', padding: 12, borderRadius: 8, marginTop: 4, borderWidth: 1, borderColor: '#bbf7d0' },

  // Inputs
  label: { fontSize: 12, fontWeight: 'bold', color: '#333', marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 10, marginTop: 4, backgroundColor: '#fff' },
  btnPrimary: { backgroundColor: '#1b4332', padding: 14, borderRadius: 10, alignItems: 'center', marginTop: 14 },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },

  // Results
  recBox: { backgroundColor: '#f0fdf4', padding: 12, borderRadius: 10, marginTop: 10, borderWidth: 1, borderColor: '#bbf7d0' },
  recName: { fontWeight: 'bold', fontSize: 15, color: '#1b4332' },
  recTips: { fontSize: 12, color: '#374151', marginTop: 4 },
  cameraDropzone: { borderWidth: 2, borderColor: '#52b788', borderStyle: 'dashed', backgroundColor: '#f4fbf7', borderRadius: 12, padding: 20, alignItems: 'center', marginVertical: 10 },
  summaryBox: { backgroundColor: '#eef7f2', padding: 14, borderRadius: 12, marginTop: 14 },

  // Scan Progress
  scanProgress: { marginTop: 14, backgroundColor: '#f0fdf4', borderRadius: 12, padding: 14 },
  scanStepRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6, opacity: 0.5 },
  scanStepActive: { opacity: 1 },
  scanStepText: { fontSize: 13, color: '#666' },

  // Label Results
  methodBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  confBarBg: { height: 6, backgroundColor: '#e5e7eb', borderRadius: 3, marginTop: 4, overflow: 'hidden' },
  confBarFill: { height: 6, borderRadius: 3 },

  // Profile
  avatarCircle: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#d8f3dc', alignItems: 'center', justifyContent: 'center' },
  logoutBtn: { backgroundColor: '#fee2e2', padding: 16, borderRadius: 12, alignItems: 'center', marginBottom: 30 },
  logoutBtnText: { color: '#dc2626', fontWeight: 'bold', fontSize: 15 },

  // Nav
  navBar: { flexDirection: 'row', height: 60, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#eee', justifyContent: 'space-around', alignItems: 'center' },
  navItem: { alignItems: 'center', justifyContent: 'center' }
});
