import cv2
import numpy as np
from tensorflow.keras.models import load_model
import mediapipe as mp

class VideoConfidenceEstimator:
    def __init__(self, model_path='confidence_measuring_photo.h5'):
        """Initialize the estimator with the pre-trained model and MediaPipe face detection."""
        self.model = load_model(model_path)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    def process_video(self, video_path, frames_per_second=2):
        """
        Process the video by sampling 1-2 frames per second and return the percentage of time a person appears confident.
        
        Args:
            video_path (str): Path to the input video file.
            frames_per_second (int): Number of frames to process per second (default: 2).
            
        Returns:
            float: Percentage of frames where the person appears confident, or 0.0 if no faces are detected.
        """
        # Open video file
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0 or fps == 0:
            print("Error: Could not read video file or invalid FPS.")
            cap.release()
            return 0.0

        # Calculate frame sampling
        frames_to_process = int(total_frames / fps * frames_per_second)  # Total frames to process
        if frames_to_process == 0:
            frames_to_process = 1  # Ensure at least one frame is processed
        frame_step = max(1, int(total_frames / frames_to_process))  # Step size to sample frames

        confident_frames = 0
        processed_frames = 0
        current_frame = 0

        while cap.isOpened() and processed_frames < frames_to_process:
            # Set the frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                break

            # Convert frame to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            results = self.face_detection.process(rgb_frame)

            if results.detections:
                # Find face with highest confidence
                best_detection = max(results.detections, key=lambda d: d.score[0])
                bbox = best_detection.location_data.relative_bounding_box

                h, w, _ = frame.shape
                x, y = int(bbox.xmin * w), int(bbox.ymin * h)
                w_box, h_box = int(bbox.width * w), int(bbox.height * h)

                # Clip coordinates to image bounds
                x, y = max(x, 0), max(y, 0)
                x2, y2 = min(x + w_box, w), min(y + h_box, h)

                # Crop and preprocess
                face_crop = frame[y:y2, x:x2]
                if face_crop.size == 0:
                    current_frame += frame_step
                    continue

                face_gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                face_resized = cv2.resize(face_gray, (48, 48))
                face_normalized = face_resized / 255.0
                face_input = np.expand_dims(face_normalized, axis=(0, -1))  # Shape: (1, 48, 48, 1)

                # Predict
                prediction = self.model.predict(face_input, verbose=0)
                if prediction[0][0] <= 0.5:  # Confident if prediction <= 0.5
                    confident_frames += 1

                processed_frames += 1

            current_frame += frame_step

        # Clean up
        cap.release()
        self.face_detection.close()

        # Calculate confidence percentage
        if processed_frames > 0:
            confidence_percentage = (confident_frames / processed_frames) * 10
            return round(confidence_percentage, 2)
        else:
            print("No faces detected in the sampled frames.")
            return 0.0

if __name__ == "__main__":
    # Example usage
    estimator = VideoConfidenceEstimator()
    video_path = 'lakshmi.mp4'  # Replace with your video file path
    confidence_rating = estimator.process_video(video_path, frames_per_second=2)
    print(confidence_rating)