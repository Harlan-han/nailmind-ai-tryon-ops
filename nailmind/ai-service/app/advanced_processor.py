"""Advanced nail try-on using MediaPipe Tasks API + realistic nail effects."""
import numpy as np
import cv2
from typing import List, Tuple, Optional
import os
import tempfile

# MediaPipe 0.10.x uses Tasks API
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
from mediapipe.tasks.python.core import base_options
import mediapipe as mp

from app.nail_effects import NailEffectRenderer


class AdvancedNailTryOn:
    """High-quality nail try-on using hand landmarks and realistic nail effects."""

    def __init__(self):
        # Initialize hand landmarker
        self._init_hand_landmarker()
        # Initialize nail effect renderer
        self.nail_renderer = NailEffectRenderer()

        # Finger tip indices in MediaPipe
        self.FINGER_CONFIGS = {
            'thumb': (4, 3, 2),
            'index': (8, 7, 6),
            'middle': (12, 11, 10),
            'ring': (16, 15, 14),
            'pinky': (20, 19, 18)
        }

    def _init_hand_landmarker(self):
        """Initialize MediaPipe HandLandmarker."""
        model_path = self._get_model_path()

        options = HandLandmarkerOptions(
            base_options=base_options.BaseOptions(model_asset_path=model_path),
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.hand_landmarker = HandLandmarker.create_from_options(options)
        print("Hand landmarker initialized")

    def _get_model_path(self) -> str:
        """Get or download hand landmarker model."""
        import urllib.request
        model_dir = os.path.join(tempfile.gettempdir(), "nailmind_models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "hand_landmarker.task")

        if not os.path.exists(model_path):
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            print(f"Downloading hand landmarker model...")
            try:
                urllib.request.urlretrieve(url, model_path)
                print(f"Model downloaded successfully")
            except Exception as e:
                print(f"Failed to download model: {e}")
                raise

        return model_path

    def process(self, hand_image: np.ndarray, design_image: np.ndarray) -> np.ndarray:
        """Process hand photo and design to generate try-on result."""
        result = hand_image.copy()
        h, w = hand_image.shape[:2]

        # Detect hands
        detected, hand_landmarks_list = self._detect_hands(hand_image)

        if not detected:
            cv2.putText(result, "未检测到手部，请上传清晰的手部照片",
                       (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return result

        # Process each hand
        for hand_landmarks in hand_landmarks_list:
            # Detect nail regions with new method
            nail_regions = self.nail_renderer.detect_nail_from_landmarks(hand_landmarks, w, h)

            for nail_region in nail_regions:
                try:
                    result = self.nail_renderer.apply_nail_effect(
                        result, design_image, nail_region, effect_type='auto'
                    )
                except Exception as e:
                    print(f"Error applying nail effect: {e}")
                    continue

        return result

    def _detect_hands(self, image: np.ndarray) -> Tuple[bool, List]:
        """Detect hands using MediaPipe Tasks API."""
        try:
            # Convert BGR to RGB
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # Detect hands
            results = self.hand_landmarker.detect(mp_image)

            if results.hand_landmarks:
                return True, results.hand_landmarks
            return False, []
        except Exception as e:
            print(f"Hand detection error: {e}")
            return False, []

    def _get_nail_regions(self, hand_landmarks, img_w: int, img_h: int) -> dict:
        """Calculate nail regions for each finger with realistic proportions."""
        nail_regions = {}

        for finger_name, (tip_idx, ip_idx, mcp_idx) in self.FINGER_CONFIGS.items():
            try:
                tip = hand_landmarks[tip_idx]
                ip = hand_landmarks[ip_idx]
                mcp = hand_landmarks[mcp_idx]

                tip_px = np.array([tip.x * img_w, tip.y * img_h])
                ip_px = np.array([ip.x * img_w, ip.y * img_h])
                mcp_px = np.array([mcp.x * img_w, mcp.y * img_h])

                # Distal phalanx length (tip to DIP)
                distal_length = np.linalg.norm(tip_px - ip_px)
                if distal_length < 3:
                    continue

                # Finger width at nail bed: use distance from tip perpendicular to finger axis
                finger_axis = ip_px - mcp_px
                finger_axis_norm = finger_axis / (np.linalg.norm(finger_axis) + 1e-6)
                perp = np.array([-finger_axis_norm[1], finger_axis_norm[0]])

                # Nail width is roughly 70-80% of finger width at nail bed
                # Estimate finger width from proximal phalanx scale
                proximal_length = np.linalg.norm(ip_px - mcp_px)
                finger_width = proximal_length * 0.22
                nail_width = max(finger_width * 0.85, distal_length * 0.55)
                # Nail height (visible nail plate) is ~60-75% of distal phalanx
                nail_height = distal_length * 0.65

                # Nail center is slightly below the fingertip (nail plate sits on distal phalanx)
                nail_direction = (tip_px - ip_px) / (distal_length + 1e-6)
                nail_center = tip_px - nail_direction * (nail_height * 0.45)

                # Angle for rotation (finger direction)
                angle = np.degrees(np.arctan2(nail_direction[1], nail_direction[0]))
                nail_angle = angle - 90  # perpendicular to finger axis

                if finger_name == 'thumb':
                    # Thumb nail is wider and oriented differently
                    nail_width = distal_length * 0.75
                    nail_height = distal_length * 0.55
                    nail_center = tip_px - nail_direction * (nail_height * 0.35)
                    nail_angle = angle

                nail_regions[finger_name] = {
                    'center': nail_center,
                    'width': int(nail_width),
                    'height': int(nail_height),
                    'angle': nail_angle,
                    'finger_direction': nail_direction
                }
            except Exception as e:
                nail_regions[finger_name] = None

        return nail_regions

    def _extract_design_colors(self, design: np.ndarray) -> np.ndarray:
        """Extract dominant colors from design image, avoiding background."""
        h, w = design.shape[:2]
        # Sample center region where nail art is more likely (avoid edges)
        margin_h = int(h * 0.15)
        margin_w = int(w * 0.15)
        center_crop = design[margin_h:h-margin_h, margin_w:w-margin_w]

        # Resize to small for faster k-means
        small = cv2.resize(center_crop, (48, 48))
        pixels = small.reshape(-1, 3).astype(np.float32)

        # K-means with k=5
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, 5, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS)

        # Score each color: prefer colorful (high saturation), not too dark/light
        counts = np.bincount(labels.flatten())
        best_score = -1
        best_color = centers[0]

        for i, color in enumerate(centers):
            b, g, r = color
            brightness = (b + g + r) / 3.0
            # Saturation in HSV space (approximate)
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            saturation = (max_c - min_c) / (max_c + 1e-6)

            # Skip near-white, near-black, and very gray colors
            if brightness < 35 or brightness > 245:
                continue
            if saturation < 0.1 and brightness > 180:
                continue  # likely white/gray background

            # Score = saturation * count (prefer colorful and frequent)
            score = saturation * counts[i]
            if score > best_score:
                best_score = score
                best_color = color

        # Fallback if all colors were filtered
        if best_score < 0:
            # Pick the one with highest saturation
            for i, color in enumerate(centers):
                r, g, b = color[2], color[1], color[0]
                max_c = max(r, g, b)
                min_c = min(r, g, b)
                saturation = (max_c - min_c) / (max_c + 1e-6)
                if saturation > best_score:
                    best_score = saturation
                    best_color = color

        return best_color.astype(np.uint8)

    def _create_nail_patch(self, width: int, height: int, color: np.ndarray) -> np.ndarray:
        """Create a nail-shaped colored patch with gloss effect."""
        # Create RGBA patch
        patch = np.zeros((height, width, 4), dtype=np.uint8)

        # Ensure color is a tuple of Python ints
        color_tuple = tuple(int(c) for c in color)

        # Draw nail shape (rounded rectangle / ellipse)
        center = (width // 2, height // 2)
        axes = (max(1, width // 2 - 2), max(1, height // 2 - 2))
        cv2.ellipse(patch, center, axes, 0, 0, 360, (*color_tuple, 255), -1)

        # Add gloss highlight (white semi-transparent arc at top)
        gloss_center = (width // 2, height // 4)
        gloss_axes = (max(1, width // 4), max(1, height // 8))
        cv2.ellipse(patch, gloss_center, gloss_axes, 0, 0, 360, (255, 255, 255, 80), -1)

        # Soften edges with Gaussian blur on alpha
        alpha = patch[:, :, 3].astype(np.float32)
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
        patch[:, :, 3] = alpha.astype(np.uint8)

        return patch

    def _apply_nail_design(self, image: np.ndarray, design: np.ndarray,
                          nail_info: dict, finger_name: str) -> np.ndarray:
        """Apply nail design color to a specific nail region."""
        try:
            center = nail_info['center'].astype(np.int32)
            width = max(4, nail_info['width'])
            height = max(4, nail_info['height'])
            angle = nail_info['angle']

            h, w = image.shape[:2]

            # Extract dominant color from design (cached by caller ideally)
            if not hasattr(self, '_design_color'):
                self._design_color = self._extract_design_colors(design)
            nail_color = self._design_color

            # Create nail patch
            patch = self._create_nail_patch(width, height, nail_color)

            # Rotate patch to match nail angle
            rotation_matrix = cv2.getRotationMatrix2D((width // 2, height // 2), -angle, 1.0)
            patch_rotated = cv2.warpAffine(
                patch, rotation_matrix, (width, height),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0, 0)
            )

            # Calculate bounding box
            x1 = center[0] - width // 2
            y1 = center[1] - height // 2
            x2 = x1 + width
            y2 = y1 + height

            # Clip to image bounds
            x1_clip, y1_clip = max(0, x1), max(0, y1)
            x2_clip, y2_clip = min(w, x2), min(h, y2)

            if x2_clip <= x1_clip or y2_clip <= y1_clip:
                return image

            roi_h = y2_clip - y1_clip
            roi_w = x2_clip - x1_clip

            # Extract ROI from image
            roi = image[y1_clip:y2_clip, x1_clip:x2_clip]

            # Extract corresponding region from rotated patch
            dx1 = max(0, -x1)
            dy1 = max(0, -y1)
            patch_roi = patch_rotated[dy1:dy1 + roi_h, dx1:dx1 + roi_w]

            if patch_roi.shape[:2] != roi.shape[:2]:
                patch_roi = cv2.resize(patch_roi, (roi_w, roi_h))

            # Separate color and alpha
            patch_rgb = patch_roi[:, :, :3].astype(np.float32)
            patch_alpha = patch_roi[:, :, 3].astype(np.float32) / 255.0

            # Blur alpha for smoother edges
            patch_alpha = cv2.GaussianBlur(patch_alpha, (3, 3), 0)
            alpha_expanded = np.expand_dims(patch_alpha, axis=-1)

            # Blend with original nail texture preserved
            roi_float = roi.astype(np.float32)

                # Boost patch color saturation for visibility
            patch_hsv = cv2.cvtColor(patch_rgb.astype(np.uint8), cv2.COLOR_BGR2HSV)
            patch_hsv[:, :, 1] = np.clip(patch_hsv[:, :, 1].astype(np.int16) + 40, 0, 255).astype(np.uint8)
            patch_rgb_boosted = cv2.cvtColor(patch_hsv, cv2.COLOR_HSV2BGR).astype(np.float32)

            # Simple strong alpha blend (preserve some original texture)
            result = roi_float * (1 - alpha_expanded * 0.85) + patch_rgb_boosted * (alpha_expanded * 0.85)
            result = np.clip(result, 0, 255)

            image[y1_clip:y2_clip, x1_clip:x2_clip] = result.astype(np.uint8)

        except Exception as e:
            print(f"Error applying nail design: {e}")

        return image

    def analyze_hand_quality(self, image: np.ndarray) -> dict:
        """Analyze hand photo quality."""
        h, w = image.shape[:2]

        detected, _ = self._detect_hands(image)

        if not detected:
            return {
                "hand_detected": False,
                "quality_score": 0.0,
                "recommendations": ["未检测到手部，请上传包含手部的照片"]
            }

        quality_score = 0.7
        recommendations = []

        # Check brightness
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)

        if brightness < 50:
            recommendations.append("照片过暗，请在光线充足的环境下拍摄")
            quality_score -= 0.15
        elif brightness > 240:
            recommendations.append("照片过曝，请避免强光直射")
            quality_score -= 0.1
        else:
            quality_score += 0.1

        # Check sharpness
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            recommendations.append("照片略显模糊，请保持手部稳定")
            quality_score -= 0.1
        else:
            quality_score += 0.1

        if not recommendations:
            recommendations.append("照片质量良好，可以开始试戴")
            quality_score = min(1.0, quality_score + 0.1)

        return {
            "hand_detected": True,
            "quality_score": round(max(0.3, min(1.0, quality_score)), 2),
            "brightness": round(brightness, 1),
            "sharpness": round(laplacian_var, 1),
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


# Singleton instance
try_on_generator = None

def get_generator():
    """Get or create the try-on generator singleton."""
    global try_on_generator
    if try_on_generator is None:
        try_on_generator = AdvancedNailTryOn()
    return try_on_generator
