import tensorflow.keras.models as keras_models
import librosa
import soundfile as sf
import numpy as np
import joblib

class AudioRatingProcessor:
    def __init__(self, model_path="Fluency and Pronunciation Rating model.keras", scaler_path="mfcc_scaler.pkl", sample_rate=22050):
        """Initialize the audio rating processor with model and scaler."""
        self.sample_rate = sample_rate
        self.model = keras_models.load_model(model_path, compile=False)
        self.scaler = joblib.load(scaler_path)
        self.min_duration = 2.0
        self.max_frames = 215
        self.silence_threshold = -40

    def extract_mfcc(self, file_path):
        """Extract MFCCs and detect silence using RMS energy."""
        try:
            audio, sr = librosa.load(file_path, sr=self.sample_rate)
            duration = librosa.get_duration(y=audio, sr=sr)

            segments = []
            if duration < self.min_duration:
                return None
            else:
                num_segments = int(np.ceil(duration / 5))
                for i in range(num_segments):
                    start = int(i * 5 * sr)
                    end = int(start + 5 * sr)
                    segment = audio[start:end]

                    if len(segment) < 5 * sr:
                        padding = int(5 * sr - len(segment))
                        segment = np.pad(segment, (0, padding))

                    rms = librosa.feature.rms(y=segment)
                    avg_db = 20 * np.log10(np.mean(rms) + 1e-9)
                    is_silent = avg_db < self.silence_threshold

                    if not is_silent:
                        mfcc = librosa.feature.mfcc(y=segment, sr=sr, n_mfcc=13, hop_length=512)
                        if mfcc.shape[1] > self.max_frames:
                            mfcc = mfcc[:, :self.max_frames]
                        else:
                            mfcc = np.pad(mfcc, ((0, 0), (0, self.max_frames - mfcc.shape[1])), mode='constant')

                        mfcc = mfcc.T
                        segments.append(mfcc)
                return segments
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None

    def convert_to_wav(self, file_path):
        """Convert audio file to WAV format if necessary."""
        if not file_path.endswith(".wav"):
            y, sr = librosa.load(file_path, sr=self.sample_rate)
            wav_path = "converted.wav"
            sf.write(wav_path, y, sr)
            return wav_path
        return file_path

    def predict_audio_rating(self, file_path):
        """Predict pronunciation and fluency scores for an audio file."""
        file_path = self.convert_to_wav(file_path)
        segments = self.extract_mfcc(file_path)
        if not segments:
            return "No usable speech found."

        X = np.array(segments)
        X_2d = X.reshape(-1, 13)
        X_scaled = self.scaler.transform(X_2d).reshape(len(X), 215, 13)

        pronun_preds, fluency_preds = self.model.predict(X_scaled)

        top_n = max(1, int(0.25 * len(pronun_preds)))
        avg_pronun = np.mean(sorted(pronun_preds.flatten())[-top_n:])
        avg_fluency = np.mean(sorted(fluency_preds.flatten())[-top_n:])

        return {
            "Pronunciation Score": round(avg_pronun, 2),
            "Fluency Score": round(avg_fluency, 2)
        }