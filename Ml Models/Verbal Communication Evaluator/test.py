from fluency_predictor import AudioRatingProcessor

def main():
    # Initialize the AudioRatingProcessor
    processor = AudioRatingProcessor(
        model_path="Fluency and Pronunciation Rating model.keras",
        scaler_path="mfcc_scaler.pkl"
    )

    # Path to the audio file you want to test
    audio_file = "converted.wav"  # Replace with actual audio file path

    # Make prediction
    result = processor.predict_audio_rating(audio_file)

    # Print the result
    if isinstance(result, str):
        print(result)
    else:
        print("Prediction Results:")
        print(f"Pronunciation Score: {result['Pronunciation Score']}")
        print(f"Fluency Score: {result['Fluency Score']}")

if __name__ == "__main__":
    main()