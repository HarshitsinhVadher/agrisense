import os
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

# Crop profiles based on Indian Agricultural Data & Kaggle Crop Recommendation Dataset
CROP_PROFILES = {
    'rice': {'N': (60, 100), 'P': (35, 60), 'K': (35, 50), 'temp': (20, 27), 'hum': (80, 90), 'ph': (6.0, 7.8), 'rain': (180, 300)},
    'maize': {'N': (60, 100), 'P': (35, 60), 'K': (15, 25), 'temp': (18, 27), 'hum': (55, 75), 'ph': (5.5, 7.0), 'rain': (60, 110)},
    'chickpea': {'N': (20, 50), 'P': (55, 80), 'K': (75, 85), 'temp': (17, 21), 'hum': (14, 20), 'ph': (6.0, 8.5), 'rain': (65, 95)},
    'kidneybeans': {'N': (15, 40), 'P': (55, 80), 'K': (15, 25), 'temp': (15, 25), 'hum': (18, 25), 'ph': (5.5, 6.0), 'rain': (60, 150)},
    'pigeonpeas': {'N': (15, 40), 'P': (55, 80), 'K': (15, 25), 'temp': (28, 38), 'hum': (30, 65), 'ph': (5.0, 7.5), 'rain': (90, 200)},
    'mothbeans': {'N': (0, 30), 'P': (35, 60), 'K': (15, 25), 'temp': (24, 32), 'hum': (40, 65), 'ph': (3.5, 10.0), 'rain': (30, 75)},
    'mungbean': {'N': (0, 30), 'P': (35, 60), 'K': (15, 25), 'temp': (27, 30), 'hum': (80, 90), 'ph': (6.2, 7.2), 'rain': (35, 60)},
    'blackgram': {'N': (40, 60), 'P': (55, 80), 'K': (15, 25), 'temp': (25, 35), 'hum': (60, 75), 'ph': (6.5, 7.8), 'rain': (60, 75)},
    'lentil': {'N': (15, 40), 'P': (55, 80), 'K': (15, 25), 'temp': (18, 30), 'hum': (60, 70), 'ph': (5.9, 7.4), 'rain': (35, 55)},
    'pomegranate': {'N': (15, 40), 'P': (10, 30), 'K': (35, 45), 'temp': (18, 25), 'hum': (85, 95), 'ph': (5.5, 7.2), 'rain': (100, 112)},
    'banana': {'N': (80, 120), 'P': (70, 95), 'K': (45, 55), 'temp': (25, 30), 'hum': (75, 85), 'ph': (5.5, 6.5), 'rain': (90, 120)},
    'mango': {'N': (0, 40), 'P': (15, 40), 'K': (25, 35), 'temp': (27, 36), 'hum': (45, 55), 'ph': (4.5, 7.0), 'rain': (89, 101)},
    'grapes': {'N': (20, 40), 'P': (120, 145), 'K': (195, 205), 'temp': (8, 40), 'hum': (80, 90), 'ph': (5.5, 6.5), 'rain': (65, 75)},
    'watermelon': {'N': (80, 120), 'P': (5, 30), 'K': (45, 55), 'temp': (24, 27), 'hum': (80, 90), 'ph': (6.0, 7.0), 'rain': (40, 60)},
    'muskmelon': {'N': (80, 120), 'P': (5, 30), 'K': (45, 55), 'temp': (27, 29), 'hum': (90, 95), 'ph': (6.0, 6.7), 'rain': (20, 30)},
    'apple': {'N': (0, 40), 'P': (120, 145), 'K': (195, 205), 'temp': (21, 24), 'hum': (90, 95), 'ph': (5.5, 6.5), 'rain': (100, 125)},
    'orange': {'N': (0, 40), 'P': (5, 30), 'K': (5, 15), 'temp': (10, 35), 'hum': (90, 95), 'ph': (6.0, 7.5), 'rain': (100, 120)},
    'papaya': {'N': (30, 70), 'P': (45, 70), 'K': (45, 55), 'temp': (23, 44), 'hum': (90, 95), 'ph': (6.5, 7.0), 'rain': (40, 250)},
    'coconut': {'N': (15, 40), 'P': (5, 30), 'K': (25, 35), 'temp': (25, 28), 'hum': (90, 98), 'ph': (5.5, 6.5), 'rain': (140, 220)},
    'cotton': {'N': (100, 140), 'P': (35, 60), 'K': (15, 25), 'temp': (22, 26), 'hum': (75, 85), 'ph': (5.8, 8.0), 'rain': (60, 90)},
    'jute': {'N': (60, 90), 'P': (35, 60), 'K': (35, 45), 'temp': (23, 26), 'hum': (70, 80), 'ph': (6.0, 7.4), 'rain': (150, 200)},
    'coffee': {'N': (80, 120), 'P': (15, 40), 'K': (25, 35), 'temp': (23, 28), 'hum': (50, 70), 'ph': (6.0, 7.5), 'rain': (110, 190)}
}

def generate_dataset(samples_per_crop=100, random_state=42):
    np.random.seed(random_state)
    data = []
    
    for crop, prof in CROP_PROFILES.items():
        n = np.random.uniform(prof['N'][0], prof['N'][1], samples_per_crop)
        p = np.random.uniform(prof['P'][0], prof['P'][1], samples_per_crop)
        k = np.random.uniform(prof['K'][0], prof['K'][1], samples_per_crop)
        temp = np.random.uniform(prof['temp'][0], prof['temp'][1], samples_per_crop)
        hum = np.random.uniform(prof['hum'][0], prof['hum'][1], samples_per_crop)
        ph = np.random.uniform(prof['ph'][0], prof['ph'][1], samples_per_crop)
        rain = np.random.uniform(prof['rain'][0], prof['rain'][1], samples_per_crop)
        
        for i in range(samples_per_crop):
            data.append({
                'N': round(n[i], 2),
                'P': round(p[i], 2),
                'K': round(k[i], 2),
                'temperature': round(temp[i], 2),
                'humidity': round(hum[i], 2),
                'ph': round(ph[i], 2),
                'rainfall': round(rain[i], 2),
                'label': crop
            })
            
    df = pd.DataFrame(data)
    return df

def train_and_save_model():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    csv_path = os.path.join(data_dir, 'crop_dataset.csv')
    
    print("Generating Crop Recommendation Dataset (2,200 samples)...")
    df = generate_dataset(samples_per_crop=100)
    df.to_csv(csv_path, index=False)
    print(f"Dataset saved to {csv_path}")
    
    X = df[['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']]
    y = df['label']
    
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
    
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=15)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model Training Accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    model_path = os.path.join(script_dir, 'crop_model.pkl')
    encoder_path = os.path.join(script_dir, 'label_encoder.pkl')
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    with open(encoder_path, 'wb') as f:
        pickle.dump(label_encoder, f)
        
    print(f"Saved trained model to {model_path}")
    print(f"Saved label encoder to {encoder_path}")

if __name__ == '__main__':
    train_and_save_model()
