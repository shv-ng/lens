import logging

import cv2
import pytesseract

from core.decorators import logit

logger = logging.getLogger(__name__)


@logit
def extract_text_from_image(image_path):
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    except Exception as e:
        logger.exception(f"Error reading image: {image_path}, error: {e}")
        return ""

    if img is None:
        logger.error(f"Error reading image: {image_path}")
        return ""

    h, w = img.shape[:2]
    if w < 1200:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    if cv2.mean(img)[0] < 127:
        img = cv2.bitwise_not(img)

    _, processed_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    custom_config = r"--oem 3 --psm 6"

    try:
        text = pytesseract.image_to_string(processed_img, config=custom_config)
    except Exception as e:
        logger.exception(f"Error extracting text from image: {image_path}, error: {e}")
        return ""

    logger.info(f"Extracted text from image: {text}")
    return text
