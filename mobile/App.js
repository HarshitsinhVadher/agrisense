import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, TextInput, Image, Modal, ActivityIndicator, Alert } from 'react-native';
import CameraScanner from './components/CameraScanner';

// Auto-detect PC LAN IP for physical mobile phone connectivity
const API_BASE_URL = 'http://192.168.16.197:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('weather');
  const [lang, setLang] = useState('en');

  // Weather State
  const [weather, setWeather] = useState(null);

  // Crop Recommendation State
  const [nVal, setNVal] = useState('80');
  const [pVal, setPVal] = useState('45');
  const [kVal, setKVal] = useState('50');
  const [phVal, setPhVal] = useState('6.5');
  const [tempVal, setTempVal] = useState('26');
  const [humVal, setHumVal] = useState('75');
  const [rainVal, setRainVal] = useState('110');
  const [recommendations, setRecommendations] = useState(null);
  const [recLoading, setRecLoading] = useState(false);

  // Soil Health OCR State
  const [soilParsed, setSoilParsed] = useState(null);
  const [soilLoading, setSoilLoading] = useState(false);

  // Label Scanner State
  const [labelText, setLabelText] = useState('');
  const [labelResult, setLabelResult] = useState(null);
  const [labelLoading, setLabelLoading] = useState(false);

  // Camera Modal State
  const [cameraVisible, setCameraVisible] = useState(false);
  const [cameraMode, setCameraMode] = useState('label');

  // Farmer Profile State
  const [farmerName, setFarmerName] = useState('Ramesh Patel');
  const [farmerPhone, setFarmerPhone] = useState('+91 98765 43210');
  const [farmerLocation, setFarmerLocation] = useState('Anand, Gujarat');

  useEffect(() => {
    fetchWeather();
    fetchProfile();
  }, []);

  const fetchWeather = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/weather?location_name=Anand,%20Gujarat`);
      const data = await res.json();
      setWeather(data);
    } catch (e) {
      console.log("Weather fetch error:", e);
    }
  };

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/profile`);
      const data = await res.json();
      if (data) {
        setFarmerName(data.name || 'Ramesh Patel');
        setFarmerPhone(data.phone || '+91 98765 43210');
        setFarmerLocation(data.location || 'Anand, Gujarat');
      }
    } catch (e) {
      console.log("Profile fetch error:", e);
    }
  };

  const handleRecommend = async () => {
    setRecLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/recommend-crop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          N: parseFloat(nVal),
          P: parseFloat(pVal),
          K: parseFloat(kVal),
          ph: parseFloat(phVal),
          temperature: parseFloat(tempVal),
          humidity: parseFloat(humVal),
          rainfall: parseFloat(rainVal)
        })
      });
      const data = await res.json();
      setRecommendations(data.recommendations);
    } catch (e) {
      Alert.alert("Error", "Could not connect to FastAPI backend server.");
    } finally {
      setRecLoading(false);
    }
  };

  const openCameraFor = (mode) => {
    setCameraMode(mode);
    setCameraVisible(true);
  };

  const handlePhotoCaptured = async (photoAsset) => {
    setCameraVisible(false);
    
    const formData = new FormData();
    formData.append('file', {
      uri: photoAsset.uri,
      name: 'scan.jpg',
      type: 'image/jpeg'
    });
    formData.append('lang', lang);

    if (cameraMode === 'label') {
      setLabelLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/scan-label`, { method: 'POST', body: formData });
        const data = await res.json();
        setLabelResult(data);
      } catch (e) {
        Alert.alert("Error", "Label OCR scan failed.");
      } finally {
        setLabelLoading(false);
      }
    } else {
      setSoilLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/parse-soil-card`, { method: 'POST', body: formData });
        const data = await res.json();
        setSoilParsed(data);
      } catch (e) {
        Alert.alert("Error", "Soil card scan failed.");
      } finally {
        setSoilLoading(false);
      }
    }
  };

  const handleScanText = async () => {
    if (!labelText.trim()) return;
    setLabelLoading(true);
    const formData = new FormData();
    formData.append('text_input', labelText);
    formData.append('lang', lang);

    try {
      const res = await fetch(`${API_BASE_URL}/api/scan-label`, { method: 'POST', body: formData });
      const data = await res.json();
      setLabelResult(data);
    } catch (e) {
      Alert.alert("Error", "Product query failed.");
    } finally {
      setLabelLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Text style={{ fontSize: 24, marginRight: 8 }}>🌱</Text>
          <View>
            <Text style={styles.brandTitle}>AgriSense</Text>
            <Text style={styles.brandSub}>Expo Go AI Assistant</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.langBadge} onPress={() => setLang(lang === 'en' ? 'gu' : (lang === 'gu' ? 'hi' : 'en'))}>
          <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 12 }}>{lang.toUpperCase()}</Text>
        </TouchableOpacity>
      </View>

      {/* Main Content */}
      <ScrollView style={styles.content}>
        {activeTab === 'weather' && (
          <View>
            <View style={styles.weatherHero}>
              <Text style={styles.locationText}>📍 {weather?.location || 'Anand, Gujarat'}</Text>
              <Text style={styles.tempText}>{weather?.current?.temperature?.toFixed(1) || '28.5'}°C</Text>
              <Text style={styles.descText}>{weather?.current?.description || 'Mainly Clear'}</Text>
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

        {activeTab === 'recommend' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>AI Crop Recommender</Text>
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

        {activeTab === 'soil' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Soil Health Card Reader</Text>
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

        {activeTab === 'scan' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Label Scanner</Text>
            <TouchableOpacity style={styles.cameraDropzone} onPress={() => openCameraFor('label')}>
              <Text style={{ fontSize: 32 }}>📷</Text>
              <Text style={{ fontWeight: 'bold', color: '#1b4332', marginTop: 4 }}>Take Photo of Product Label</Text>
            </TouchableOpacity>

            <TextInput style={styles.input} placeholder="Or enter product name (e.g. Urea, Chlorpyrifos)" value={labelText} onChangeText={setLabelText} />
            <TouchableOpacity style={styles.btnPrimary} onPress={handleScanText}>
              <Text style={styles.btnText}>🔍 Analyze Label</Text>
            </TouchableOpacity>

            {labelLoading && <ActivityIndicator size="large" color="#1b4332" style={{ marginTop: 10 }} />}

            {labelResult && (
              <View style={styles.summaryBox}>
                <Text style={styles.recName}>🏷️ {labelResult.matched_product?.name}</Text>
                <Text style={{ marginTop: 4 }}>🧪 Active: {labelResult.matched_product?.active_ingredient}</Text>
                <Text style={{ marginTop: 4 }}>💧 Dosage: {labelResult.matched_product?.dosage}</Text>
                <Text style={{ marginTop: 8, fontStyle: 'italic' }}>🤖 AI Advice: {labelResult.ai_summary}</Text>
              </View>
            )}
          </View>
        )}

        {activeTab === 'profile' && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Farmer Profile</Text>
            <Text style={styles.label}>Name</Text>
            <TextInput style={styles.input} value={farmerName} onChangeText={setFarmerName} />
            <Text style={styles.label}>Phone</Text>
            <TextInput style={styles.input} value={farmerPhone} onChangeText={setFarmerPhone} />
            <Text style={styles.label}>Location</Text>
            <TextInput style={styles.input} value={farmerLocation} onChangeText={setFarmerLocation} />
          </View>
        )}
      </ScrollView>

      {/* Bottom Nav */}
      <View style={styles.navBar}>
        {['weather', 'recommend', 'soil', 'scan', 'profile'].map((tab) => (
          <TouchableOpacity key={tab} style={styles.navItem} onPress={() => setActiveTab(tab)}>
            <Text style={{ fontSize: 20 }}>{tab === 'weather' ? '🌤️' : tab === 'recommend' ? '🌱' : tab === 'soil' ? '📄' : tab === 'scan' ? '🏷️' : '👤'}</Text>
            <Text style={{ fontSize: 10, color: activeTab === tab ? '#1b4332' : '#666', fontWeight: 'bold' }}>{tab.toUpperCase()}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Embedded Camera Modal */}
      <Modal visible={cameraVisible} animationType="slide">
        <CameraScanner
          modeTitle={cameraMode === 'label' ? "Scan Product Label" : "Scan Soil Health Card"}
          onPhotoCaptured={handlePhotoCaptured}
          onClose={() => setCameraVisible(false)}
        />
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f4f8f5' },
  header: { paddingTop: 45, paddingBottom: 15, paddingHorizontal: 20, backgroundColor: '#1b4332', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  brandTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  brandSub: { color: '#52b788', fontSize: 11 },
  langBadge: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  content: { flex: 1, padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16, elevation: 2 },
  cardTitle: { fontSize: 16, fontWeight: 'bold', color: '#1b4332', marginBottom: 6 },
  cardSub: { fontSize: 12, color: '#666', marginBottom: 12 },
  weatherHero: { backgroundColor: '#2d6a4f', borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 16 },
  locationText: { color: '#d8f3dc', fontSize: 14, fontWeight: 'bold' },
  tempText: { color: '#fff', fontSize: 44, fontWeight: 'bold', marginVertical: 4 },
  descText: { color: '#fff', fontSize: 14 },
  advisoryBox: { backgroundColor: '#fffbe6', borderLeftWidth: 4, borderLeftColor: '#f59e0b', padding: 10, borderRadius: 6, marginVertical: 4 },
  advTitle: { fontWeight: 'bold', fontSize: 13, color: '#b45309' },
  advMsg: { fontSize: 12, color: '#374151', marginTop: 2 },
  label: { fontSize: 12, fontWeight: 'bold', color: '#333', marginTop: 8 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 10, marginTop: 4, backgroundColor: '#fff' },
  btnPrimary: { backgroundColor: '#1b4332', padding: 14, borderRadius: 10, alignItems: 'center', marginTop: 14 },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  recBox: { backgroundColor: '#f0fdf4', padding: 12, borderRadius: 10, marginTop: 10, borderWidth: 1, borderColor: '#bbf7d0' },
  recName: { fontWeight: 'bold', fontSize: 15, color: '#1b4332' },
  recTips: { fontSize: 12, color: '#374151', marginTop: 4 },
  cameraDropzone: { borderWidth: 2, borderColor: '#52b788', borderStyle: 'dashed', backgroundColor: '#f4fbf7', borderRadius: 12, padding: 20, alignItems: 'center', marginVertical: 10 },
  summaryBox: { backgroundColor: '#eef7f2', padding: 12, borderRadius: 10, marginTop: 12 },
  navBar: { flexDirection: 'row', height: 60, backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#eee', justifyContent: 'space-around', alignItems: 'center' },
  navItem: { alignItems: 'center', justifyContent: 'center' }
});
