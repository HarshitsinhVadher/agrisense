import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image, ActivityIndicator, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

export default function CameraScanner({ onPhotoCaptured, onClose, modeTitle = "Scan Label / Soil Card" }) {
  const [loading, setLoading] = useState(false);

  const takePhotoWithCamera = async () => {
    try {
      const permissionResult = await ImagePicker.requestCameraPermissionsAsync();
      if (permissionResult.granted === false) {
        Alert.alert("Permission Required", "Camera access is required to take photos of labels and soil cards.");
        return;
      }

      setLoading(true);
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        onPhotoCaptured(result.assets[0]);
      }
    } catch (e) {
      console.error("Camera error:", e);
      Alert.alert("Camera Error", "Could not launch camera.");
    } finally {
      setLoading(false);
    }
  };

  const pickImageFromGallery = async () => {
    try {
      setLoading(true);
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        onPhotoCaptured(result.assets[0]);
      }
    } catch (e) {
      console.error("Gallery picker error:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerBar}>
        <Text style={styles.headerText}>{modeTitle}</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
          <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 18 }}>✕</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.body}>
        <Text style={styles.iconText}>📷</Text>
        <Text style={styles.titleText}>Capture Document or Label</Text>
        <Text style={styles.subtitleText}>Choose camera to take a photo or select an existing image from your gallery.</Text>

        {loading ? (
          <ActivityIndicator size="large" color="#52b788" style={{ marginVertical: 30 }} />
        ) : (
          <View style={styles.btnContainer}>
            <TouchableOpacity style={styles.btnPrimary} onPress={takePhotoWithCamera}>
              <Text style={styles.btnText}>📸 Open Camera</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.btnSecondary} onPress={pickImageFromGallery}>
              <Text style={styles.btnTextSecondary}>🖼️ Choose from Gallery</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#081c15' },
  headerBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 50, paddingBottom: 20, backgroundColor: '#1b4332' },
  headerText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  closeBtn: { padding: 8 },
  body: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  iconText: { fontSize: 64, marginBottom: 16 },
  titleText: { color: '#fff', fontSize: 20, fontWeight: 'bold', textAlign: 'center', marginBottom: 8 },
  subtitleText: { color: '#a3b18a', fontSize: 13, textAlign: 'center', marginBottom: 32, paddingHorizontal: 20 },
  btnContainer: { width: '100%', gap: 14 },
  btnPrimary: { backgroundColor: '#2d6a4f', paddingVertical: 16, borderRadius: 12, alignItems: 'center' },
  btnSecondary: { backgroundColor: '#52b788', paddingVertical: 16, borderRadius: 12, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  btnTextSecondary: { color: '#081c15', fontWeight: 'bold', fontSize: 16 }
});
