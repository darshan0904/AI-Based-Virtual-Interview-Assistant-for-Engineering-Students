from voice_confidence_predictor import VoiceConfidencePredictor

audio_file = "C:\\Users\\rahul\\Downloads\\motivation.mp3"  # Replace with actual path
predictor = VoiceConfidencePredictor(audio_file)
result = predictor.predict()

if result["label"] is not None:
    print(f"Label: {result['label']}")
    print(f"Confidence: {result['confidence']:.4f}")
    with open('prediction_result.txt', 'w') as f:
        f.write(f"Label: {result['label']}\n")
        f.write(f"Confidence: {result['confidence']:.4f}\n")
else:
    print("Prediction failed.")
