import os
import pickle
import numpy as np

CROP_DETAILS = {
    'rice': {'name': 'Rice (ડાંગર / धान)', 'category': 'Cereal', 'season': 'Kharif', 'water': 'High', 'tips': 'Requires standing water during early growth phase. High N requirement.'},
    'maize': {'name': 'Maize (મકાઈ / मक्का)', 'category': 'Cereal', 'season': 'Kharif/Rabi', 'water': 'Medium', 'tips': 'Good drainage is essential. Avoid waterlogging at seedling stage.'},
    'chickpea': {'name': 'Chickpea (ચણા / चना)', 'category': 'Pulse', 'season': 'Rabi', 'water': 'Low', 'tips': 'Fixes atmospheric nitrogen. Avoid excessive irrigation during flowering.'},
    'kidneybeans': {'name': 'Kidney Beans (રાજમા / राजमा)', 'category': 'Pulse', 'season': 'Rabi', 'water': 'Medium', 'tips': 'Requires well-drained loamy soil with rich organic matter.'},
    'pigeonpeas': {'name': 'Pigeon Peas (તુવેર / अरहर)', 'category': 'Pulse', 'season': 'Kharif', 'water': 'Low-Medium', 'tips': 'Deep taproot system makes it highly drought tolerant. Intercropping friendly.'},
    'mothbeans': {'name': 'Moth Beans (મઠ / मोठ)', 'category': 'Pulse', 'season': 'Kharif', 'water': 'Very Low', 'tips': 'Extremely drought resistant. Performs well in sandy arid soils.'},
    'mungbean': {'name': 'Mung Bean (મગ / मूंग)', 'category': 'Pulse', 'season': 'Kharif/Summer', 'water': 'Low', 'tips': 'Short duration crop (60-70 days). Excellent soil enricher.'},
    'blackgram': {'name': 'Black Gram (અડદ / उड़द)', 'category': 'Pulse', 'season': 'Kharif/Rabi', 'water': 'Low-Medium', 'tips': 'Prefers neutral to slightly alkaline pH. Good green manure crop.'},
    'lentil': {'name': 'Lentil (મસૂર / मसूर)', 'category': 'Pulse', 'season': 'Rabi', 'water': 'Low', 'tips': 'Tolerates cool temperatures. Requires phosphorus-rich basal application.'},
    'pomegranate': {'name': 'Pomegranate (દાડમ / अनार)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium', 'tips': 'Thrives in warm dry climates. Requires strict pruning & drainage.'},
    'banana': {'name': 'Banana (કેળા / केला)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'High', 'tips': 'High Potassium demand. Heavy feeder crop needing frequent drip irrigation.'},
    'mango': {'name': 'Mango (કેરી / आम)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium', 'tips': 'Requires deep well-drained soil. Withhold water 2 months prior to flowering.'},
    'grapes': {'name': 'Grapes (દ્રાક્ષ / अंगूर)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium', 'tips': 'High Potassium & Phosphorus requirement. Needs trellising and pruning.'},
    'watermelon': {'name': 'Watermelon (તરબૂચ / तरबूज)', 'category': 'Fruit', 'season': 'Summer', 'water': 'Medium', 'tips': 'Sandy loam soil preferred. Requires full sunlight and warm weather.'},
    'muskmelon': {'name': 'Muskmelon (શક્કરટેટી / खरबूजा)', 'category': 'Fruit', 'season': 'Summer', 'water': 'Medium', 'tips': 'High temperature promotes sweetness. Avoid foliage wetting.'},
    'apple': {'name': 'Apple (સફરજન / सेब)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium-High', 'tips': 'Requires chilling hours and temperate cool climate with pH 5.5-6.5.'},
    'orange': {'name': 'Orange (સંતરા / संतरा)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium', 'tips': 'Citrus fruit requiring micro-nutrient sprays (Zinc, Iron, Manganese).'},
    'papaya': {'name': 'Papaya (પપૈયા / पपीता)', 'category': 'Fruit', 'season': 'Perennial', 'water': 'Medium', 'tips': 'Fast growing fruit tree. Highly sensitive to water stagnation at collar.'},
    'coconut': {'name': 'Coconut (નાળિયેર / नारियल)', 'category': 'Plantation', 'season': 'Perennial', 'water': 'High', 'tips': 'Requires humid coastal or riverine tropical climate. Salt tolerant.'},
    'cotton': {'name': 'Cotton (કપાસ / कपास)', 'category': 'Cash Crop', 'season': 'Kharif', 'water': 'Medium', 'tips': 'Black cotton soil ideal. Deep tillage and sucking pest management vital.'},
    'jute': {'name': 'Jute (શણ / पटसन)', 'category': 'Cash Crop', 'season': 'Kharif', 'water': 'High', 'tips': 'Requires warm humid climate (>70% humidity) and alluvial soil.'},
    'coffee': {'name': 'Coffee (કોફી / कॉफी)', 'category': 'Plantation', 'season': 'Perennial', 'water': 'Medium-High', 'tips': 'Shade lover tree crop. Requires acidic to neutral rich organic soil.'}
}

class CropRecommender:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, 'crop_model.pkl')
        encoder_path = os.path.join(script_dir, 'label_encoder.pkl')
        
        self.model = None
        self.encoder = None
        
        if os.path.exists(model_path) and os.path.exists(encoder_path):
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            with open(encoder_path, 'rb') as f:
                self.encoder = pickle.load(f)
                
    def predict(self, N: float, P: float, K: float, temperature: float, humidity: float, ph: float, rainfall: float):
        if self.model is None or self.encoder is None:
            # Fallback heuristic recommendation if model hasn't been trained yet
            return self._heuristic_fallback(N, P, K, temperature, humidity, ph, rainfall)
            
        features = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        probs = self.model.predict_proba(features)[0]
        
        # Top 3 crop indices
        top_indices = np.argsort(probs)[::-1][:3]
        
        results = []
        for idx in top_indices:
            crop_id = self.encoder.classes_[idx]
            confidence = float(probs[idx] * 100)
            details = CROP_DETAILS.get(crop_id, {'name': crop_id.capitalize(), 'category': 'General', 'season': 'All', 'water': 'Medium', 'tips': 'Standard agricultural practices.'})
            
            results.append({
                'crop_id': crop_id,
                'name': details['name'],
                'confidence': round(confidence, 1),
                'category': details['category'],
                'season': details['season'],
                'water_requirement': details['water'],
                'tips': details['tips']
            })
            
        return results

    def _heuristic_fallback(self, N, P, K, temperature, humidity, ph, rainfall):
        # Heuristic rules if model binary is missing
        candidates = []
        if rainfall > 150:
            candidates = ['rice', 'jute', 'coconut']
        elif N > 80 and K > 40:
            candidates = ['cotton', 'banana', 'maize']
        elif P > 50:
            candidates = ['chickpea', 'pigeonpeas', 'blackgram']
        else:
            candidates = ['mango', 'watermelon', 'papaya']
            
        results = []
        for i, c in enumerate(candidates):
            details = CROP_DETAILS.get(c, {'name': c.capitalize(), 'category': 'General', 'season': 'Kharif', 'water': 'Medium', 'tips': ''})
            results.append({
                'crop_id': c,
                'name': details['name'],
                'confidence': round(85.0 - (i * 12.0), 1),
                'category': details['category'],
                'season': details['season'],
                'water_requirement': details['water'],
                'tips': details['tips']
            })
        return results
