"""Enhanced nail art effects using OpenCV and image processing.

This module provides realistic nail art effects including:
- French tips (法式)
- Gradient (渐变)
- Cat eye (猫眼)
- Solid colors with gloss
- Glitter effects
"""
import numpy as np
import cv2
from typing import Tuple, Optional, List
import colorsys


class NailEffectRenderer:
    """Render realistic nail art effects."""

    def __init__(self):
        self.effect_presets = {
            'french': self._render_french_tip,
            'gradient': self._render_gradient,
            'cat_eye': self._render_cat_eye,
            'solid': self._render_solid,
            'glitter': self._render_glitter,
        }

    def detect_nail_from_landmarks(self, hand_landmarks, img_w: int, img_h: int) -> List[dict]:
        """Detect nail regions more accurately from hand landmarks."""
        nail_regions = []

        # MediaPipe hand landmark indices
        finger_tips = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky
        finger_pips = [2, 6, 10, 14, 18]  # PIP joints

        for i, (tip_idx, pip_idx) in enumerate(zip(finger_tips, finger_pips)):
            try:
                tip = hand_landmarks[tip_idx]
                pip = hand_landmarks[pip_idx]

                tip_px = np.array([tip.x * img_w, tip.y * img_h])
                pip_px = np.array([pip.x * img_w, pip.y * img_h])

                # Calculate finger direction
                finger_vec = tip_px - pip_px
                finger_len = np.linalg.norm(finger_vec)

                if finger_len < 5:
                    continue

                finger_dir = finger_vec / finger_len

                # Nail is perpendicular to finger direction
                perp_dir = np.array([-finger_dir[1], finger_dir[0]])

                # Nail dimensions (in pixels, relative to finger length)
                nail_width = finger_len * 0.55  # Width of nail
                nail_height = finger_len * 0.45  # Visible nail plate height

                # Nail center (slightly back from tip)
                nail_center = tip_px - finger_dir * (nail_height * 0.5)

                # Calculate angle
                angle = np.degrees(np.arctan2(finger_dir[1], finger_dir[0]))

                # For thumb, adjust angle
                if i == 0:  # Thumb
                    angle -= 30

                nail_regions.append({
                    'center': nail_center.astype(np.int32),
                    'width': int(nail_width),
                    'height': int(nail_height),
                    'angle': angle,
                    'finger_direction': finger_dir,
                    'finger_name': ['thumb', 'index', 'middle', 'ring', 'pinky'][i]
                })

            except Exception as e:
                continue

        return nail_regions

    def apply_nail_effect(self, hand_image: np.ndarray, design_image: np.ndarray,
                          nail_region: dict, effect_type: str = 'auto') -> np.ndarray:
        """Apply nail art effect to a specific nail region."""
        result = hand_image.copy()

        # Ensure minimum nail size
        width = max(nail_region['width'], 10)
        height = max(nail_region['height'], 10)
        nail_region = {**nail_region, 'width': width, 'height': height}

        # Analyze design to determine effect type
        if effect_type == 'auto':
            effect_type = self._analyze_design_type(design_image)

        # Get nail mask
        nail_mask = self._create_nail_mask(width, height, nail_region['angle'])

        # Extract color from design
        dominant_color = self._extract_nail_color(design_image)
        secondary_color = self._extract_secondary_color(design_image)

        # Render effect
        if effect_type in self.effect_presets:
            nail_patch = self.effect_presets[effect_type](
                width, height,
                dominant_color, secondary_color
            )
        else:
            nail_patch = self._render_solid(
                width, height,
                dominant_color
            )

        # Apply to image
        result = self._composite_nail(result, nail_patch, nail_mask, nail_region)

        return result

    def _analyze_design_type(self, design_image: np.ndarray) -> str:
        """Analyze design image to determine best effect type."""
        h, w = design_image.shape[:2]
        center = design_image[h//3:h*2//3, w//3:w*2//3]

        # Convert to HSV for analysis
        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)

        # Check for gradient (variance in brightness)
        brightness = hsv[:, :, 2]
        brightness_var = np.std(brightness)

        # Check for multiple distinct colors
        mean_saturation = np.mean(hsv[:, :, 1])

        # Check for sparkle/glitter
        gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
        _, sparkle_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        sparkle_ratio = np.sum(sparkle_mask > 0) / sparkle_mask.size

        # Determine type
        if sparkle_ratio > 0.05:
            return 'glitter'
        elif brightness_var > 40:
            return 'gradient'
        elif mean_saturation < 30:
            return 'french'  # Likely nude/french style
        else:
            return 'solid'

    def _extract_nail_color(self, design_image: np.ndarray) -> Tuple[int, int, int]:
        """Extract dominant nail color from design."""
        # Sample center region
        h, w = design_image.shape[:2]
        center = design_image[h//4:h*3//4, w//4:w*3//4]

        # Convert to RGB for k-means
        rgb = cv2.cvtColor(center, cv2.COLOR_BGR2RGB)
        pixels = rgb.reshape(-1, 3)

        # Find dominant color
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels.astype(np.float32), 5, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        # Find the most saturated non-skin color
        counts = np.bincount(labels.flatten())
        best_idx = 0
        best_score = -1

        for i, center in enumerate(centers):
            r, g, b = center
            # Calculate saturation
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            saturation = (max_val - min_val) / (max_val + 1) if max_val > 0 else 0
            brightness = (r + g + b) / 3

            # Skip very dark, very light, or skin-toned colors
            if brightness < 40 or brightness > 240:
                continue
            if 80 < r < 200 and 60 < g < 160 and 50 < b < 140:
                # Likely skin tone, reduce score
                saturation *= 0.3

            score = saturation * counts[i]
            if score > best_score:
                best_score = score
                best_idx = i

        return tuple(centers[best_idx].astype(np.uint8))

    def _extract_secondary_color(self, design_image: np.ndarray) -> Tuple[int, int, int]:
        """Extract secondary color (for gradients/tips)."""
        # Sample top region (for french tips)
        h, w = design_image.shape[:2]
        top = design_image[:h//3, :]

        gray = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
        _, white_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # Check if there's significant white
        white_ratio = np.sum(white_mask > 0) / white_mask.size

        if white_ratio > 0.1:
            return (240, 240, 235)  # White/cream for tips
        else:
            # Find another color
            return self._extract_nail_color(design_image)

    def _create_nail_mask(self, width: int, height: int, angle: float) -> np.ndarray:
        """Create a realistic nail-shaped mask."""
        # Ensure minimum size
        width = max(width, 8)
        height = max(height, 8)

        mask = np.zeros((height, width), dtype=np.uint8)

        # Create nail shape (rounded rectangle with curved tip)
        center = (width // 2, height // 2)

        # Draw nail shape with safe axes values
        axes = (max(2, width//2 - 2), max(2, height//2 - 2))
        cv2.ellipse(mask, center, axes, angle, 0, 360, 255, -1)

        # Refine with actual nail contour
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours[0]:
            # Smooth the contour
            contour = contours[0][0]
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            mask = np.zeros_like(mask)
            cv2.fillPoly(mask, [approx], 255)

        return mask

    def _render_solid(self, width: int, height: int,
                      color: Tuple[int, int, int],
                      secondary_color: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Render solid nail color with gloss effect."""
        # Create base patch
        patch = np.full((height, width, 3), color, dtype=np.uint8)

        # Add natural nail texture (subtle)
        noise = np.random.normal(0, 3, (height, width, 3)).astype(np.int16)
        patch = np.clip(patch.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Add gloss highlight at top
        gloss = np.zeros((height, width), dtype=np.uint8)
        for y in range(height // 4):
            alpha = 1.0 - (y / (height // 4))
            gloss[y, :] = int(255 * alpha * 0.4)

        # Apply gloss
        gloss_bgr = cv2.cvtColor(gloss, cv2.COLOR_GRAY2BGR)
        patch = cv2.addWeighted(patch, 1.0, gloss_bgr, 0.3, 0)

        # Add cuticle shadow at bottom
        shadow_height = min(10, height // 6)
        for y in range(height - shadow_height, height):
            alpha = (y - (height - shadow_height)) / shadow_height
            shadow_color = tuple(int(c * (1 - alpha * 0.3)) for c in color)
            patch[y, :] = shadow_color

        return patch

    def _render_french_tip(self, width: int, height: int,
                           base_color: Tuple[int, int, int],
                           tip_color: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Render French tip manicure effect."""
        if tip_color is None:
            tip_color = (245, 240, 235)  # Classic white/cream tip

        # Create base
        patch = np.full((height, width, 3), base_color, dtype=np.uint8)

        # Add tip color (top portion)
        tip_start = int(height * 0.35)

        # Create curved tip
        for y in range(tip_start):
            # Curve the tip line
            curve_offset = int(np.sin((y / tip_start) * np.pi) * 3)
            actual_y = y + curve_offset

            if 0 <= actual_y < tip_start:
                # Blend tip color
                alpha = 0.9
                patch[y, :] = cv2.addWeighted(
                    patch[y, :].astype(np.float32),
                    1 - alpha,
                    np.array(tip_color, dtype=np.float32),
                    alpha,
                    0
                ).astype(np.uint8)

        # Add subtle gloss
        gloss = np.zeros((height, width), dtype=np.uint8)
        for y in range(height // 5):
            alpha = 1.0 - (y / (height // 5))
            gloss[y, :] = int(255 * alpha * 0.3)

        patch = cv2.addWeighted(patch, 1.0, cv2.cvtColor(gloss, cv2.COLOR_GRAY2BGR), 0.2, 0)

        return patch

    def _render_gradient(self, width: int, height: int,
                         color1: Tuple[int, int, int],
                         color2: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Render gradient effect."""
        if color2 is None:
            # Create lighter version of color1
            hls = colorsys.rgb_to_hls(color1[0]/255, color1[1]/255, color1[2]/255)
            color2 = tuple(int(c * 255) for c in colorsys.hls_to_rgb(hls[0], min(1, hls[1] * 1.4), hls[2]))

        # Create gradient
        patch = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            alpha = y / height
            r = int(color1[0] * (1 - alpha) + color2[0] * alpha)
            g = int(color1[1] * (1 - alpha) + color2[1] * alpha)
            b = int(color1[2] * (1 - alpha) + color2[2] * alpha)
            patch[y, :] = [r, g, b]

        # Add gloss
        gloss = np.zeros((height, width), dtype=np.uint8)
        for y in range(height // 3):
            alpha = 1.0 - (y / (height // 3))
            gloss[y, :] = int(255 * alpha * 0.35)

        patch = cv2.addWeighted(patch, 1.0, cv2.cvtColor(gloss, cv2.COLOR_GRAY2BGR), 0.25, 0)

        return patch

    def _render_cat_eye(self, width: int, height: int,
                       base_color: Tuple[int, int, int],
                       accent_color: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Render cat eye effect (magnetic line effect)."""
        # Base color (usually dark)
        patch = np.full((height, width, 3), base_color, dtype=np.uint8)

        # Create metallic streak in center
        center_x = width // 2
        streak_width = max(3, width // 5)

        for x in range(max(0, center_x - streak_width), min(width, center_x + streak_width)):
            dist = abs(x - center_x) / streak_width
            alpha = max(0, 1 - dist)

            # Bright streak color
            streak = tuple(int(c + (255 - c) * alpha * 0.8) for c in base_color)

            for y in range(height):
                # Vertical fade for cat eye effect
                y_alpha = 1 - abs(y - height // 2) / (height // 2)
                y_alpha = max(0, y_alpha)

                final_alpha = alpha * y_alpha
                patch[y, x] = tuple(
                    int(base_color[i] + (streak[i] - base_color[i]) * final_alpha)
                    for i in range(3)
                )

        # Add gloss
        if height > 3 and width > 3:
            ksize = min(3, width - 1 if width % 2 == 0 else width)
            ksize = max(3, ksize if ksize % 2 == 1 else ksize - 1)
            patch = cv2.GaussianBlur(patch, (ksize, ksize), 0)

        return patch

    def _render_glitter(self, width: int, height: int,
                       base_color: Tuple[int, int, int],
                       glitter_color: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """Render glitter/sparkle effect."""
        patch = np.full((height, width, 3), base_color, dtype=np.uint8)

        # Add glitter particles
        num_particles = int(width * height * 0.01)  # 1% coverage

        for _ in range(num_particles):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            size = np.random.randint(1, 3)
            brightness = np.random.randint(180, 256)

            # Draw glitter particle
            cv2.circle(patch, (x, y), size, (brightness, brightness, brightness), -1)

        # Add overall shimmer
        noise = np.random.normal(0, 10, (height, width, 3)).astype(np.int16)
        patch = np.clip(patch.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Blur slightly for soft glitter look
        if height > 3 and width > 3:
            patch = cv2.GaussianBlur(patch, (3, 3), 0)

        return patch

    def _composite_nail(self, hand_image: np.ndarray, nail_patch: np.ndarray,
                       nail_mask: np.ndarray, nail_region: dict) -> np.ndarray:
        """Composite nail patch onto hand image."""
        result = hand_image.copy()
        h, w = hand_image.shape[:2]

        cx, cy = nail_region['center']
        width = nail_region['width']
        height = nail_region['height']
        angle = nail_region['angle']

        # Calculate bounding box
        x1 = cx - width // 2
        y1 = cy - height // 2
        x2 = x1 + width
        y2 = y1 + height

        # Clip to image bounds
        x1_clip = max(0, x1)
        y1_clip = max(0, y1)
        x2_clip = min(w, x2)
        y2_clip = min(h, y2)

        if x2_clip <= x1_clip or y2_clip <= y1_clip:
            return result

        roi_w = x2_clip - x1_clip
        roi_h = y2_clip - y1_clip

        # Skip if ROI is too small
        if roi_w < 3 or roi_h < 3:
            return result

        # Extract ROI
        roi = result[y1_clip:y2_clip, x1_clip:x2_clip]

        # Resize nail patch to ROI
        patch_resized = cv2.resize(nail_patch, (roi_w, roi_h))
        mask_resized = cv2.resize(nail_mask, (roi_w, roi_h))

        # Normalize mask to 0-1
        mask_norm = mask_resized.astype(np.float32) / 255.0

        # Smooth mask edges (ensure kernel size is valid)
        ksize = min(5, roi_w - 1 if roi_w % 2 == 0 else roi_w)
        ksize = max(3, ksize if ksize % 2 == 1 else ksize - 1)
        mask_norm = cv2.GaussianBlur(mask_norm, (ksize, ksize), 0)

        mask_norm = np.expand_dims(mask_norm, axis=-1)

        # Blend
        roi_float = roi.astype(np.float32)
        patch_float = patch_resized.astype(np.float32)

        blended = roi_float * (1 - mask_norm) + patch_float * mask_norm
        blended = np.clip(blended, 0, 255).astype(np.uint8)

        # Apply to result
        result[y1_clip:y2_clip, x1_clip:x2_clip] = blended

        return result
