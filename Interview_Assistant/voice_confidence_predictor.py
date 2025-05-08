import os
import numpy as np
import librosa
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

class VoiceConfidencePredictor:
    def __init__(self, audio_path: str, model_path: str = 'C:\\Users\\rahul\\Desktop\\AI-Based-Virtual-Interview-Preparation-Assistant\\Ml Models\\Confidence Prediction\\voice_confidence_model.h5', max_len: int = 500):
        self.audio_path = audio_path
        self.model_path = model_path
        self.max_len = max_len

    def _extract_mfcc(self, n_mfcc: int = 40):
        try:
            audio, sample_rate = librosa.load(self.audio_path, sr=None)
            mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=n_mfcc)
            return mfccs.T
        except Exception as e:
            print(f"Error extracting MFCCs: {e}")
            return None

    def predict(self) -> dict:
        try:
            mfcc = self._extract_mfcc()
            if mfcc is None:
                return {"label": None, "confidence": None}

            mfcc_padded = pad_sequences([mfcc], maxlen=self.max_len, padding='post', dtype='float32')
            X = np.array(mfcc_padded)

            model = load_model(self.model_path)
            y_pred_prob = model.predict(X)[0][0]
            y_pred_class = 1 if y_pred_prob > 0.5 else 0
            label = "Confident" if y_pred_class == 1 else "Underconfident"

            return {"label": label, "confidence": float(y_pred_prob)}

        except Exception as e:
            print(f"Prediction error: {e}")
            return {"label": None, "confidence": None}
