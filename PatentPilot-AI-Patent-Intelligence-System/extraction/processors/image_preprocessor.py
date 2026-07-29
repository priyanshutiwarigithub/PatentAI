import cv2
import numpy as np
from PIL import Image
from loguru import logger

class ImagePreprocessor:
    """
    Applies a series of image enhancement techniques to improve OCR accuracy
    on scanned documents, microscopy images, and handwritten lab notebooks.
    """

    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Full preprocessing pipeline."""
        logger.info("Starting image preprocessing pipeline")
        
        image = self._upscale_if_needed(image)
        image = self._convert_to_grayscale(image)
        image = self._denoise(image)
        image = self._deskew(image)
        image = self._apply_adaptive_threshold(image)
        image = self._remove_borders(image)
        
        logger.info("Image preprocessing complete")
        return image

    def _upscale_if_needed(self, image: np.ndarray, min_width: int = 1000) -> np.ndarray:
        """Upscale small images to improve OCR accuracy."""
        h, w = image.shape[:2]
        if w < min_width:
            scale = min_width / w
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logger.debug(f"Upscaled image from {w}x{h} to {new_w}x{new_h}")
        return image

    def _convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Non-local means denoising for scanned documents."""
        return cv2.fastNlMeansDenoising(image, h=10, templateWindowSize=7, searchWindowSize=21)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Automatically corrects document skew using Hough Line Transform.
        Scanned documents are often slightly tilted.
        """
        coords = np.column_stack(np.where(image < 128))  # dark pixels
        if len(coords) == 0:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > 0.5:  # only correct if skew is significant
            h, w = image.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            image = cv2.warpAffine(image, M, (w, h),
                                   flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
            logger.debug(f"Deskewed image by {angle:.2f} degrees")
        return image

    def _apply_adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Adaptive thresholding handles uneven lighting in scanned docs
        better than global thresholding.
        """
        return cv2.adaptiveThreshold(
            image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

    def _remove_borders(self, image: np.ndarray, border_size: int = 10) -> np.ndarray:
        """Remove scanner border artifacts."""
        return image[border_size:-border_size, border_size:-border_size]

    def pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    def cv2_to_pil(self, cv2_image: np.ndarray) -> Image.Image:
        if len(cv2_image.shape) == 2:
            return Image.fromarray(cv2_image)
        return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))