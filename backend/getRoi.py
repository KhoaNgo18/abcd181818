import cv2
import numpy as np
import pyautogui
import time
import sys

# Global variables for ROI selection
roi = None
selecting = False
start_point = [0, 0]
end_point = [0, 0]

def select_roi(image_path = None, image = None):
    global roi, selecting, start_point, end_point
    
    if image is None and image_path is None:
        print("Either image_path or image should be provided")
        return
    
    def mouse_callback(event, x, y, flags, param):
        global selecting, start_point, end_point, roi
        
        if event == cv2.EVENT_LBUTTONDOWN:
            selecting = True
            start_point = [x, y]
        elif event == cv2.EVENT_MOUSEMOVE and selecting:
            end_point = [x, y]
        elif event == cv2.EVENT_LBUTTONUP:
            selecting = False
            end_point = [x, y]
            roi = [start_point, end_point]
    
    if image_path is not None:
        image = cv2.imread(image_path)
        
    clone = image.copy()
    cv2.namedWindow("Select Region")
    cv2.setMouseCallback("Select Region", mouse_callback)
    
    while True:
        temp_image = clone.copy()
        if selecting or roi is not None:
            cv2.rectangle(temp_image, start_point, end_point, (0, 255, 0), 2)
        cv2.imshow("Select Region", temp_image)
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter key to confirm selection
            break
    
    cv2.destroyAllWindows()
    return roi

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_roi.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    roi = select_roi(image_path)
    print(roi)