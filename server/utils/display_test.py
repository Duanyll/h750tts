import cv2

image = cv2.imread('D:/Downloads/dcim/frametest/image10.jpg')
height, width, _ = image.shape
directions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
# draw directions: histogram overlay on bottom of image
histogram_width = width // len(directions)
histogram_height = height // 4
for i in range(len(directions)):
    cv2.rectangle(image, (i * histogram_width, int(height - histogram_height *
        directions[i])), ((i + 1) * histogram_width, height), (255, 255, 255), -1)
cv2.imwrite('fuck.jpg', image)