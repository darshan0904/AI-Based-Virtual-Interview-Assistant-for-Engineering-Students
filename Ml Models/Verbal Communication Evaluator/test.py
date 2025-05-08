from fluency_predictor import SpeechRatingPredictor

def main():
    # Initialize predictor
    predictor = SpeechRatingPredictor(
        model_path="Fluency and Pronunciation Rating model.keras",
        scaler_path="mfcc_scaler.pkl",
        sample_rate=22050
    )
    
    # Specify the path to your sample audio file
    audio_file = "motivation.mp3"  # Replace with the actual path to your audio file
    
    # Make prediction
    result = predictor.predict(audio_file)
    
    # Print results
    if "error" in result:
        print(result["error"])
    else:
        print(f"Pronunciation Score: {result['Pronunciation Score']}")
        print(f"Fluency Score: {result['Fluency Score']}")

if __name__ == "__main__":
    main()