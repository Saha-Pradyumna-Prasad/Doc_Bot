import os
import re
from flask import Flask, render_template, request, jsonify
from dataset import MEDICAL_DATASET, SYNONYMS_MAPPING, DEFAULT_REPLY

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))

def is_bengali(text):
    return bool(re.search(r'[\u0980-\u09FF]', text))

def process_medical_input(user_text):
    if not user_text:
        return None
        
    # ১. ইউজারের ইনপুট টেক্সট একদম ক্লিন ও নরমাল করা
    cleaned_text = re.sub(r'[,\-।?!_./\\;:]', ' ', user_text.lower()).strip()
    cleaned_text = " ".join(cleaned_text.split())  # ডাবল বা ট্রিপল স্পেস থাকলে সিঙ্গেল স্পেস করা
    words = cleaned_text.split()
    
    # ২. ফুল ফ্রেজ ম্যাচিং (Case-insensitive & Safe Mapping)
    # প্রথমে মূল মেডিকেল ডেটাসেট চেক
    for key in list(MEDICAL_DATASET.keys()):
        normalized_key = " ".join(key.lower().split()).strip()
        if normalized_key == cleaned_text or normalized_key in cleaned_text or cleaned_text in normalized_key:
            return MEDICAL_DATASET[key]
            
    # ৩. সিনোনিমস ম্যাপিং ডিকশনারি চেক (ফ্রেজ লেভেলে)
    for sync_key, main_key in list(SYNONYMS_MAPPING.items()):
        normalized_sync = " ".join(sync_key.lower().split()).strip()
        normalized_main = " ".join(main_key.lower().split()).strip()
        
        if normalized_sync == cleaned_text or normalized_sync in cleaned_text or cleaned_text in normalized_sync:
            # মেইন কী-এর সাথে রিয়েল ডেটাসেট কী-এর সেফ ম্যাচিং
            for real_key in list(MEDICAL_DATASET.keys()):
                if " ".join(real_key.lower().split()).strip() == normalized_main:
                    return MEDICAL_DATASET[real_key]
            if main_key in MEDICAL_DATASET:
                return MEDICAL_DATASET[main_key]

    # ৪. সিঙ্গেল ওয়ার্ড ফলব্যাক ম্যাচিং (যদি পুরো বাক্যের কোনো একটা শব্দও মিলে যায়)
    for word in words:
        for key in list(MEDICAL_DATASET.keys()):
            if word == " ".join(key.lower().split()).strip():
                return MEDICAL_DATASET[key]
                
        for sync_key, main_key in list(SYNONYMS_MAPPING.items()):
            if word == " ".join(sync_key.lower().split()).strip():
                normalized_main = " ".join(main_key.lower().split()).strip()
                for real_key in list(MEDICAL_DATASET.keys()):
                    if " ".join(real_key.lower().split()).strip() == normalized_main:
                        return MEDICAL_DATASET[real_key]
                if main_key in MEDICAL_DATASET:
                    return MEDICAL_DATASET[main_key]
                    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_support')
def video_support():
    return render_template('video_support.html')

@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'মেসেজ পাওয়া যায়নি!'}), 400
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'ফাঁকা মেসেজ পাঠানো সম্ভব নয়'}), 400

        user_lang = "bn" if is_bengali(user_message) else "en"
        matched_result = process_medical_input(user_message)

        if list_found := matched_result:
            if user_lang == "bn":
                response_text = (
                    f"📋 **প্রধান লক্ষণসমূহ:**\n{list_found.get('symptoms', 'তথ্য নেই।')}\n\n"
                    f"🩹 **জরুরি প্রাথমিক চিকিৎসা:**\n{list_found.get('first_aid', 'তথ্য নেই।')}\n\n"
                    f"🌿 **ঘরোয়া সমাধান:**\n{list_found.get('home_remedy', 'তথ্য নেই।')}\n\n"
                    f"🩺 **পরামর্শের জন্য কোন ডাক্তার দেখাবেন:**\n↳ {list_found.get('specialist', 'জেনারেল ফিজিশিয়ান')}\n\n"
                    f"⚠️ **মেডিকেল সতর্কতা:**\n{list_found.get('medication_hint', 'তথ্য নেই।')}\n\n"
                    f"🚨 **জরুরি বিপদের লক্ষণ (অবçalves হাসপাতালে যান):**\n{list_found.get('warning_signs', 'তথ্য নেই।')}"
                )
            else:
                response_text = (
                    f"📋 **Primary Symptoms:**\n{list_found.get('symptoms', 'Not available.')}\n\n"
                    f"🩹 **First Aid Management:**\n{list_found.get('first_aid', 'Not available.')}\n\n"
                    f"🌿 **Home Remedies:**\n{list_found.get('home_remedy', 'Not available.')}\n\n"
                    f"🩺 **Recommended Specialist:**\n↳ {list_found.get('specialist', 'General Physician')}\n\n"
                    f"⚠️ **Medication Caution:**\n{list_found.get('medication_hint', 'Not available.')}\n\n"
                    f"🚨 **Warning Signs (Seek Emergency Care):**\n{list_found.get('warning_signs', 'Not available.')}"
                )
            return jsonify({'response': response_text})
        else:
            fallback = DEFAULT_REPLY[user_lang]
            response_text = (
                f"{fallback.get('reply', 'No match found.')}\n\n"
                f"🩺 **Suggested General Action:**\n↳ {fallback.get('specialist', 'General Physician')}\n\n"
                f"🚨 **Note:** {fallback.get('disclaimer', 'No details.')}"
            )
            return jsonify({'response': response_text})

    except Exception as e:
        print(f"\n❌ [LOCAL SERVER ERROR]: {str(e)}\n")
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
