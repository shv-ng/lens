import cv2
import pytesseract


def extract_text_from_screenshot(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    h, w = img.shape[:2]
    if w < 1200:
        img = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    if cv2.mean(img)[0] < 127:
        img = cv2.bitwise_not(img)

    _, processed_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    custom_config = r"--oem 3 --psm 6"

    text = pytesseract.image_to_string(processed_img, config=custom_config)

    return text


if __name__ == "__main__":
    tweet_text = extract_text_from_screenshot("test.png")
    print("--- Extracted Screenshot Text ---")
    print(tweet_text)
