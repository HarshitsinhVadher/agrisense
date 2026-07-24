import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image, ActivityIndicator } from 'react-native';
import { Camera } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';

export default function CameraScanner({ onPhotoCaptured, onClose, modeTitle = "Scan Label / Soil Card" }) {
  const [hasPermission, setHasPermission] = useState(null);
  const [cameraRef, setCameraRef] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  const takePicture = async () => {
    if (cameraRef) {
      setLoading(true);
      try {
        const photo = await cameraRef.takePictureAsync({ quality: 0.8 });
        onPhotoCaptured(photo);
      } catch (e) {
        console.error("Camera capture error:", e);
      } finally {
        setLoading(false);
      }
    }
  };

  const pickImageFromGallery = async () => {
    setLoading(true);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
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

  if (hasPermission === null) {
    return <View style={styles.container}><Text style={styles.text}>Requesting camera permission...</Text></View>;
  }
  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>No access to camera.</Text>
        <TouchableOpacity style={styles.btnSecondary} onPress={pickImageFromGallery}>
          <Text style={styles.btnText}>📁 Choose from Gallery</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.btnClose} onPress={onClose}>
          <Text style={styles.btnText}>Close</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Camera style={styles.camera} ref={ref => setCameraRef(ref)}>
        <View style={styles.headerBar}>
          <Text style={styles.headerText}>{modeTitle}</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={{ color: '#fff', fontWeight: 'bold' }}>✕</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.overlayFrame}>
          <View style={styles.cornerTL} />
          <View style={styles.cornerTR} />
          <View style={styles.cornerBL} />
          <View style={styles.cornerBR} />
        </View>

        <View style={styles.controlsBar}>
          <TouchableOpacity style={styles.galleryBtn} onPress={pickImageFromGallery}>
            <Text style={{ fontSize: 24 }}>🖼️</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.shutterBtn} onPress={takePicture} disabled={loading}>
            {loading ? <ActivityIndicator color="#1b4332" /> : <View style={styles.shutterInner} />}
          </TouchableOpacity>
        </View>
      </Camera>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1, justifyContent: 'space-between' },
  headerBar: { flexDirection: 'row', justifyContent: 'space-between', padding: 20, paddingTop: 50, backgroundColor: 'rgba(0,0,0,0.5)' },
  headerText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  closeBtn: { padding: 8 },
  overlayFrame: { alignSelf: 'center', width: 280, height: 280, borderStyle: 'dashed', borderWidth: 1, borderColor: 'rgba(255,255,255,0.4)', borderRadius: 16 },
  controlsBar: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', paddingBottom: 40, backgroundColor: 'rgba(0,0,0,0.5)' },
  galleryBtn: { padding: 12 },
  shutterBtn: { width: 72, height: 72, borderRadius: 36, backgroundColor: '#fff', justifyContent: 'center', alignItems: 'center' },
  shutterInner: { width: 60, height: 60, borderRadius: 30, backgroundColor: '#2d6a4f', borderWidth: 2, borderColor: '#fff' },
  text: { color: '#fff', textAlign: 'center', marginTop: 100 },
  btnSecondary: { backgroundColor: '#2d6a4f', padding: 12, borderRadius: 8, margin: 20, alignItems: 'center' },
  btnClose: { backgroundColor: '#666', padding: 12, borderRadius: 8, marginHorizontal: 20, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: 'bold' }
});
