"""Image processing utilities for nail try-on."""
import numpy as np
import cv2
from PIL import Image
import mediapipe as mp
from typing import List, Tuple, Optional
import io


class HandDetector:
    """Hand detection and landmark extraction using MediaPipe Tasks API."""

    def __init__(self):
        # Use MediaPipe Tasks API
        self.BaseOptions = mp.tasks.BaseOptions
        self.HandLandmarker = mp.tasks.vision.HandLandmarker
        self.HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        self.VisionRunningMode = mp.tasks.vision.RunningMode
        # Drawing utils removed - not needed for processing

        # Download model if not exists
        model_path = self._get_model_path()

        # Initialize hand landmarker
        options = self.HandLandmarkerOptions(
            base_options=self.BaseOptions(model_asset_path=model_path),
            running_mode=self.VisionRunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.5
        )
        self.landmarker = self.HandLandmarker.create_from_options(options)

    def _get_model_path(self) -> str:
        """Get or download hand landmarker model."""
        import os
        import tempfile
        # Use temp directory to avoid Chinese characters in path
        model_dir = os.path.join(tempfile.gettempdir(), "nailmind_models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "hand_landmarker.task")

        if not os.path.exists(model_path):
            # Download model
            import urllib.request
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            print(f"Downloading hand landmarker model to {model_path}...")
            urllib.request.urlretrieve(url, model_path)
            print(f"Model downloaded successfully")

        return model_path

    def detect_hands(self, image: np.ndarray) -> Tuple[bool, List]:
        """Detect hands in image and return landmarks."""
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image_rgb.shape[:2]

        # Create MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        # Detect hands
        results = self.landmarker.detect(mp_image)

        if results.hand_landmarks:
            return True, results.hand_landmarks
        return False, []

    def get_finger_regions(self, hand_landmarks, image_shape: Tuple[int, int]) -> List[dict]:
        """Get bounding regions for each fingernail."""
        h, w = image_shape[:2]
        regions = []

        # MediaPipe hand landmark indices
        # 4: thumb_tip, 3: thumb_ip, 2: thumb_mcp
        # 8: index_tip, 7: index_dip, 6: index_pip
        # 12: middle_tip, 11: middle_dip, 10: middle_pip
        # 16: ring_tip, 15: ring_dip, 14: ring_pip
        # 20: pinky_tip, 19: pinky_dip, 18: pinky_pip

        finger_configs = [
            (4, 3, 2, "thumb"),
            (8, 6, 5, "index"),
            (12, 10, 9, "middle"),
            (16, 14, 13, "ring"),
            (20, 18, 17, "pinky")
        ]

        for tip_idx, pip_idx, mcp_idx, name in finger_configs:
            tip = hand_landmarks[tip_idx]
            pip = hand_landmarks[pip_idx]
            mcp = hand_landmarks[mcp_idx]

            tip_x = int(tip.x * w)
            tip_y = int(tip.y * h)
            pip_x = int(pip.x * w)
            pip_y = int(pip.y * h)
            mcp_x = int(mcp.x * w)
            mcp_y = int(mcp.y * h)

            # Calculate nail region
            nail_length = abs(tip_y - pip_y) * 1.2
            nail_width = nail_length * 0.9

            center_x = (tip_x + pip_x) // 2
            center_y = (tip_y + pip_y) // 2

            x1 = int(center_x - nail_width // 2)
            y1 = int(center_y - nail_length // 2)
            x2 = int(center_x + nail_width // 2)
            y2 = int(center_y + nail_length // 2)

            # Ensure bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)

            if x2 > x1 and y2 > y1:
                regions.append({
                    "finger": name,
                    "bbox": (x1, y1, x2, y2),
                    "center": (center_x, center_y),
                    "angle": np.degrees(np.arctan2(tip_y - mcp_y, tip_x - mcp_x))
                })

        return regions


class NailTryOnGenerator:
    """Generate nail try-on results by overlaying designs onto hand photos."""

    def __init__(self):
        self.hand_detector = HandDetector()

    def process(self, hand_image: np.ndarray, design_image: np.ndarray) -> np.ndarray:
        """
        Process hand photo and design to generate try-on result.

        Args:
            hand_image: Hand photo (BGR format from OpenCV)
            design_image: Nail design image (BGR format)

        Returns:
            Result image with design applied to nails
        """
        result = hand_image.copy()

        # Detect hands
        detected, hand_landmarks_list = self.hand_detector.detect_hands(hand_image)

        if not detected:
            # Return original image with text if no hands detected
            h, w = hand_image.shape[:2]
            cv2.putText(
                result,
                "No hand detected - please upload a clear hand photo",
                (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            return result

        # Process each hand
        for hand_landmarks in hand_landmarks_list:
            regions = self.hand_detector.get_finger_regions(
                hand_landmarks,
                hand_image.shape
            )

            for region in regions:
                x1, y1, x2, y2 = region["bbox"]
                angle = region["angle"]

                if x2 <= x1 or y2 <= y1:
                    continue

                # Resize design to fit nail region
                nail_width = x2 - x1
                nail_height = y2 - y1

                if nail_width <= 0 or nail_height <= 0:
                    continue

                # Rotate design based on finger angle
                design_resized = cv2.resize(design_image, (nail_width, nail_height))

                # Apply simple color-based overlay
                roi = result[y1:y2, x1:x2]

                if roi.shape[:2] != design_resized.shape[:2]:
                    continue

                # Create overlay based on color similarity to natural nail
                # This is a simplified approach - production should use segmentation
                alpha = 0.6

                # Use color distance to create mask
                if design_resized.shape[2] == 3:
                    # Convert to HSV for better color handling
                    design_hsv = cv2.cvtColor(design_resized, cv2.COLOR_BGR2HSV)

                    # Create a simple mask excluding very light/white areas
                    brightness = design_hsv[:, :, 2]
                    mask = (brightness < 240).astype(np.float32) * alpha

                    mask_3ch = np.stack([mask] * 3, axis=-1)
                    blended = (roi * (1 - mask_3ch) +
                              design_resized * mask_3ch).astype(np.uint8)
                    result[y1:y2, x1:x2] = blended
                else:
                    # Use alpha channel if available
                    alpha_ch = design_resized[:, :, 3:] / 255.0 * alpha
                    result[y1:y2, x1:x2] = (
                        roi * (1 - alpha_ch) +
                        design_resized[:, :, :3] * alpha_ch
                    ).astype(np.uint8)

        return result

    def analyze_hand_quality(self, image: np.ndarray) -> dict:
        """Analyze hand photo quality for try-on suitability."""
        detected, landmarks = self.hand_detector.detect_hands(image)

        if not detected:
            return {
                "hand_detected": False,
                "quality_score": 0,
                "recommendations": ["请上传包含清晰手部的照片"]
            }

        # Calculate quality metrics
        h, w = image.shape[:2]
        max_hand_ratio = 0

        for hand_landmarks in landmarks:
            x_coords = [lm.x for lm in hand_landmarks]
            y_coords = [lm.y for lm in hand_landmarks]

            hand_width = (max(x_coords) - min(x_coords)) * w
            hand_height = (max(y_coords) - min(y_coords)) * h
            hand_area = hand_width * hand_height

            max_hand_ratio = max(max_hand_ratio, hand_area / (h * w))

        quality_score = min(1.0, max_hand_ratio * 5)  # Scale ratio to score
        quality_score = max(0.3, quality_score)  # Minimum score if hand detected

        recommendations = []

        if max_hand_ratio < 0.05:
            recommendations.append("手部占比太小，建议近距离拍摄")
        elif max_hand_ratio > 0.9:
            recommendations.append("手部占比过大，建议稍微远离一些")

        # Check brightness
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        if brightness < 50:
            recommendations.append("照片过暗，请在光线充足的环境下拍摄")
            quality_score *= 0.7
        elif brightness > 240:
            recommendations.append("照片过曝，请避免强光直射")
            quality_score *= 0.8

        # Check sharpness
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            recommendations.append("照片略显模糊，请保持手部稳定")
            quality_score *= 0.8

        if not recommendations:
            recommendations.append("照片质量良好，可以开始试戴")

        return {
            "hand_detected": True,
            "quality_score": round(quality_score, 2),
            "hand_ratio": round(max_hand_ratio, 3),
            "brightness": round(brightness, 1),
            "sharpness": round(laplacian_var, 1),
            "num_hands": len(landmarks),
            "recommendations": recommendations
        }


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Load image from bytes."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image from bytes")
    return image


def save_image_to_bytes(image: np.ndarray, format: str = ".jpg") -> bytes:
    """Save image to bytes."""
    success, buffer = cv2.imencode(format, image)
    if success:
        return buffer.tobytes()
    raise ValueError("Failed to encode image")
