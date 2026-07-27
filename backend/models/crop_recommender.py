import os
import pickle
import numpy as np

CROP_DETAILS = {
    'rice': {
        'name': 'Rice', 'name_gu': 'ડાંગર (ચોખા)', 'name_hi': 'धान (चावल)',
        'category': 'Cereal', 'category_gu': 'ધાન્ય પાક', 'category_hi': 'अनाज',
        'season': 'Kharif', 'season_gu': 'ચોમાસું (ખરીફ)', 'season_hi': 'खरीफ',
        'water': 'High', 'water_gu': 'વધુ (ભરપૂર)', 'water_hi': 'उच्च',
        'tips': 'Requires standing water during early growth phase. High N requirement.',
        'tips_gu': 'શરૂઆતના વિકાસ તબક્કે પાણી ભરેલું રાખવું જરૂરી. નાઇટ્રોજનની વધુ જરૂરિયાત.',
        'tips_hi': 'प्रारंभिक वृद्धि चरण के दौरान खड़े पानी की आवश्यकता होती है। उच्च N की आवश्यकता।'
    },
    'maize': {
        'name': 'Maize', 'name_gu': 'મકાઈ', 'name_hi': 'मक्का',
        'category': 'Cereal', 'category_gu': 'ધાન્ય પાક', 'category_hi': 'अनाज',
        'season': 'Kharif/Rabi', 'season_gu': 'ખરીફ / રબી', 'season_hi': 'खरीफ/रबी',
        'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
        'tips': 'Good drainage is essential. Avoid waterlogging at seedling stage.',
        'tips_gu': 'જમીનમાં નિતાર હોવો જરૂરી. રોપા તબક્કે પાણી ભરાઈ ન રહેવું જોઈએ.',
        'tips_hi': 'अच्छी जल निकासी आवश्यक है। पौध अवस्था में जलभराव से बचें।'
    },
    'chickpea': {
        'name': 'Chickpea', 'name_gu': 'ચણા', 'name_hi': 'चना',
        'category': 'Pulse', 'category_gu': 'કઠોળ', 'category_hi': 'दलहन',
        'season': 'Rabi', 'season_gu': 'શિયાળુ (રબી)', 'season_hi': 'रबी',
        'water': 'Low', 'water_gu': 'ઓછું', 'water_hi': 'कम',
        'tips': 'Fixes atmospheric nitrogen. Avoid excessive irrigation during flowering.',
        'tips_gu': 'હવામાંથી નાઇટ્રોજન સ્થિર કરે છે. ફૂલ આવવાના સમયે વધુ પિયત ન આપવું.',
        'tips_hi': 'वायुमंडलीय नाइट्रोजन को स्थिर करता है। फूल आने के दौरान अत्यधिक सिंचाई से बचें।'
    },
    'cotton': {
        'name': 'Cotton', 'name_gu': 'કપાસ', 'name_hi': 'कपास',
        'category': 'Cash Crop', 'category_gu': 'રોકડિયો પાક', 'category_hi': 'नकदी फसल',
        'season': 'Kharif', 'season_gu': 'ચોમાસું (ખરીફ)', 'season_hi': 'खरीफ',
        'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
        'tips': 'Black cotton soil ideal. Deep tillage and sucking pest management vital.',
        'tips_gu': 'કાળી જમીન શ્રેષ્ઠ. ઉંડી ખેડ અને ચુસિયા જીવાતનું નિયંત્રણ જરૂરી.',
        'tips_hi': 'काली कपास मिट्टी आदर्श है। गहरी जुताई और चूसक कीट प्रबंधन महत्वपूर्ण है।'
    },
    'pigeonpeas': {
        'name': 'Pigeon Peas', 'name_gu': 'તુવેર', 'name_hi': 'अरहर (तुअर)',
        'category': 'Pulse', 'category_gu': 'કઠોળ', 'category_hi': 'दलहन',
        'season': 'Kharif', 'season_gu': 'ચોમાસું (ખરીફ)', 'season_hi': 'खरीफ',
        'water': 'Low-Medium', 'water_gu': 'ઓછું-મધ્યમ', 'water_hi': 'कम-मध्यम',
        'tips': 'Deep taproot system makes it highly drought tolerant. Intercropping friendly.',
        'tips_gu': 'ઉંડા મૂળને કારણે ગુજારો કરી શકે છે. આંતરપાક તરીકે વાવેતર માટે ઉત્તમ.',
        'tips_hi': 'गहरी मूसला जड़ प्रणाली इसे अत्यधिक सूखा सहनशील बनाती है।'
    },
    'mungbean': {
        'name': 'Mung Bean', 'name_gu': 'મગ', 'name_hi': 'मूंग',
        'category': 'Pulse', 'category_gu': 'કઠોળ', 'category_hi': 'दलहन',
        'season': 'Kharif/Summer', 'season_gu': 'ખરીફ / ઉનાળુ', 'season_hi': 'खरीफ/ग्रीष्म',
        'water': 'Low', 'water_gu': 'ઓછું', 'water_hi': 'कम',
        'tips': 'Short duration crop (60-70 days). Excellent soil enricher.',
        'tips_gu': 'ટૂંકા ગાળાનો પાક (૬૦-૭૦ દિવસ). જમીનની ફળદ્રુપતા વધારે છે.',
        'tips_hi': 'कम अवधि की फसल (60-70 दिन)। उत्कृष्ट मिट्टी समृद्धकर्ता।'
    },
    'watermelon': {
        'name': 'Watermelon', 'name_gu': 'તરબૂચ', 'name_hi': 'तरबूज',
        'category': 'Fruit', 'category_gu': 'ફળ પાક', 'category_hi': 'फल',
        'season': 'Summer', 'season_gu': 'ઉનાળુ', 'season_hi': 'ग्रीष्म',
        'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
        'tips': 'Sandy loam soil preferred. Requires full sunlight and warm weather.',
        'tips_gu': 'રેતાળ ગોરાડુ જમીન અનુકૂળ. તડકો અને ગરમી જરૂરી.',
        'tips_hi': 'बलुई दोमट मिट्टी को प्राथमिकता दी जाती है। पूर्ण सूर्य के प्रकाश की आवश्यकता।'
    },
    'mango': {
        'name': 'Mango', 'name_gu': 'કેરી (આંબો)', 'name_hi': 'आम',
        'category': 'Fruit', 'category_gu': 'ફળ પાક', 'category_hi': 'फल',
        'season': 'Perennial', 'season_gu': 'બારમાસી', 'season_hi': 'सदाबहार',
        'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
        'tips': 'Requires deep well-drained soil. Withhold water 2 months prior to flowering.',
        'tips_gu': 'ઉંડી ફળદ્રુપ જમીન અનુકૂળ. મોર આવવાના ૨ મહિના પહેલાં પિયત બંધ રાખવું.',
        'tips_hi': 'गहरी अच्छी जल निकासी वाली मिट्टी की आवश्यकता होती है।'
    }
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
                
    def predict(self, N: float, P: float, K: float, temperature: float, humidity: float, ph: float, rainfall: float, lang: str = "en"):
        if self.model is None or self.encoder is None:
            return self._heuristic_fallback(N, P, K, temperature, humidity, ph, rainfall, lang)
            
        features = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        probs = self.model.predict_proba(features)[0]
        
        top_indices = np.argsort(probs)[::-1][:3]
        
        results = []
        for idx in top_indices:
            crop_id = self.encoder.classes_[idx]
            confidence = float(probs[idx] * 100)
            details = CROP_DETAILS.get(crop_id, {
                'name': crop_id.capitalize(), 'name_gu': crop_id.capitalize(), 'name_hi': crop_id.capitalize(),
                'category': 'General', 'category_gu': 'સામાન્ય', 'category_hi': 'सामान्य',
                'season': 'All', 'season_gu': 'તમામ', 'season_hi': 'सभी',
                'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
                'tips': 'Standard agricultural practices.', 'tips_gu': 'સામાન્ય ખેતી પદ્ધતિઓ.', 'tips_hi': 'मानक कृषि पद्धतियाँ।'
            })
            
            results.append({
                'crop_id': crop_id,
                'name': details.get(f'name_{lang}', details['name']),
                'confidence': round(confidence, 1),
                'category': details.get(f'category_{lang}', details['category']),
                'season': details.get(f'season_{lang}', details['season']),
                'water_requirement': details.get(f'water_{lang}', details['water']),
                'tips': details.get(f'tips_{lang}', details['tips'])
            })
            
        return results

    def _heuristic_fallback(self, N, P, K, temperature, humidity, ph, rainfall, lang="en"):
        candidates = []
        if rainfall > 150:
            candidates = ['rice', 'cotton']
        elif N > 80 and K > 40:
            candidates = ['cotton', 'maize']
        elif P > 50:
            candidates = ['chickpea', 'pigeonpeas', 'mungbean']
        else:
            candidates = ['mango', 'watermelon']
            
        results = []
        for i, c in enumerate(candidates):
            details = CROP_DETAILS.get(c, {
                'name': c.capitalize(), 'name_gu': c.capitalize(), 'name_hi': c.capitalize(),
                'category': 'General', 'category_gu': 'સામાન્ય', 'category_hi': 'सामान्य',
                'season': 'Kharif', 'season_gu': 'ચોમાસું', 'season_hi': 'खरीफ',
                'water': 'Medium', 'water_gu': 'મધ્યમ', 'water_hi': 'मध्यम',
                'tips': '', 'tips_gu': '', 'tips_hi': ''
            })
            results.append({
                'crop_id': c,
                'name': details.get(f'name_{lang}', details['name']),
                'confidence': round(88.0 - (i * 10.0), 1),
                'category': details.get(f'category_{lang}', details['category']),
                'season': details.get(f'season_{lang}', details['season']),
                'water_requirement': details.get(f'water_{lang}', details['water']),
                'tips': details.get(f'tips_{lang}', details['tips'])
            })
        return results
