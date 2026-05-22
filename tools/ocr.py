import cv2
import pytesseract

# Load image in grayscale
img = cv2.imread('blurry_invoice.png', cv2.IMREAD_GRAYSCALE)

# Apply thresholding to make it purely stark black and white
# (This removes shadows and background noise)
processed_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

# Feed the cleaned image into Tesseract
text = pytesseract.image_to_string(processed_img)
print(text)
