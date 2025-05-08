import numpy as np
import librosa
import soundfile as sf
from tensorflow.keras.models import load_model
import joblib

class SpeechRatingPredictor:
    def __init__(self, model_path="Fluency and Pronunciation Rating model.keras", scaler_path="mfcc_scaler.pkl", sample_rate=22050):
        """
        Initialize the predictor with paths to the model and scaler.
        
        Args:
            model_path (str): Path to the trained Keras model.
            scaler_path (str): Path to the saved MFCC scaler.
            sample_rate (int): Sampling rate for audio processing.
        """
        self.model = load_model(model_path, compile=False)
        self.scaler = joblib.load(scaler_path)
        self.sample_rate = sample_rate
        self.max_length = 215  # Fixed length for MFCC frames (from your model)
        
    def extract_mfcc(self, file_path):
        """
        Extract MFCC features from an audio file.
        
        Args:
            file_path (str): Path to the audio file.
            
        Returns:
            list: List of MFCC feature arrays for valid segments.
        """
        try:
            # Load audio
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            
            # Convert to WAV if not already
            if not file_path.endswith(".wav"):
                wav_path = "temp_converted.wav"
                sf.write(wav_path, y, sr)
                y, sr = librosa.load(wav_path, sr=self.sample_rate)
            
            # Segment audio into 5-second chunks
            segment_length = 5 * sr
            segments = []
            
            for start in range(0, len(y), segment_length):
                segment = y[start:start + segment_length]
                if len(segment) < segment_length:
                    segment = np.pad(segment, (0, segment_length - len(segment)), mode='constant')
                
                # Extract MFCC
                mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13, n_fft=2048, hop_length=512)
                
                # Pad or truncate to fixed length
                if mfcc.shape[1] < self.max_length:
                    mfcc = np.pad(mfcc, ((0, 0), (0, self.max_length - mfcc.shape[1])), mode='constant')
                else:
                    mfcc = mfcc[:, :self.max_length]
                
                segments.append(mfcc)
            
            return segments
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    def predict(self, file_path):
        """
        Predict pronunciation and fluency scores for an audio file.
        
        Args:
            file_path (str): Path to the audio file.
            
        Returns:
            dict: Dictionary containing pronunciation and fluency scores, or error message.
        """
        segments = self.extract_mfcc(file_path)
        if not segments:
            return {"error": "No usable speech found."}
        
        # Prepare features
        X = np.array(segments)
        X_2d = X.reshape(-1, 13)
        X_scaled = self.scaler.transform(X_2d).reshape(len(X), self.max_length, 13)
        
        # Make predictions
        pronun_preds, fluency_preds = self.model.predict(X_scaled)
        
        # Use top 25% scores
        top_n = max(1, int(0.25 * len(pronun_preds)))
        avg_pronun = np.mean(sorted(pronun_preds.flatten())[-top_n:])
        avg_fluency = np.mean(sorted(fluency_preds.flatten())[-top_n:])
        
        return {
            "Pronunciation Score": round(avg_pronun, 2),
            "Fluency Score": round(avg_fluency, 2)
        }