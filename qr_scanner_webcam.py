import cv2
import argparse
import os
import sys
import time
import numpy as np

# Using OpenCV's QR code detector only
print("Using OpenCV's QRCodeDetector for QR code detection")


def decode_qr_codes(frame):
    """Detect and decode QR codes in a frame using OpenCV"""
    detected_codes = []
    
    # Use OpenCV's QRCodeDetector (QR codes only)
    qr_detector = cv2.QRCodeDetector()
    
    # Try detecting multiple QR codes first
    try:
        retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(frame)
        
        if retval:
            for i, data in enumerate(decoded_info):
                if data:  # Skip empty strings
                    pts = points[i].astype(int)
                    x_min, y_min = np.min(pts[:, 0]), np.min(pts[:, 1])
                    x_max, y_max = np.max(pts[:, 0]), np.max(pts[:, 1])
                    w, h = x_max - x_min, y_max - y_min
                    
                    polygon = [(int(p[0]), int(p[1])) for p in pts]
                    
                    rect_obj = type('obj', (object,), {
                        'left': int(x_min),
                        'top': int(y_min),
                        'width': int(w),
                        'height': int(h)
                    })
                    
                    detected_codes.append({
                        'data': data,
                        'type': 'QRCODE',
                        'rect': rect_obj,
                        'polygon': polygon
                    })
    except Exception as e:
        # Fallback to single QR code detection if multi-detection fails
        try:
            data, bbox, straight_qrcode = qr_detector.detectAndDecode(frame)
            if data and bbox is not None:
                pts = bbox.astype(int).reshape(-1, 2)
                x_min, y_min = np.min(pts[:, 0]), np.min(pts[:, 1])
                x_max, y_max = np.max(pts[:, 0]), np.max(pts[:, 1])
                w, h = x_max - x_min, y_max - y_min
                
                polygon = [(int(p[0]), int(p[1])) for p in pts]
                
                rect_obj = type('obj', (object,), {
                    'left': int(x_min),
                    'top': int(y_min),
                    'width': int(w),
                    'height': int(h)
                })
                
                detected_codes.append({
                    'data': data,
                    'type': 'QRCODE',
                    'rect': rect_obj,
                    'polygon': polygon
                })
        except Exception as e:
            print(f"Error in QR detection: {e}")
            
    # Try with image preprocessing if no codes detected
    if not detected_codes:
        try:
            # Convert to grayscale if not already
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # Try different preprocessing techniques
            preprocessed_frames = [
                cv2.GaussianBlur(gray, (5, 5), 0),  # Blurred
                cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),  # Adaptive threshold
                cv2.equalizeHist(gray)  # Histogram equalization
            ]
            
            for processed_frame in preprocessed_frames:
                data, bbox, straight_qrcode = qr_detector.detectAndDecode(processed_frame)
                if data and bbox is not None:
                    pts = bbox.astype(int).reshape(-1, 2)
                    x_min, y_min = np.min(pts[:, 0]), np.min(pts[:, 1])
                    x_max, y_max = np.max(pts[:, 0]), np.max(pts[:, 1])
                    w, h = x_max - x_min, y_max - y_min
                    
                    polygon = [(int(p[0]), int(p[1])) for p in pts]
                    
                    rect_obj = type('obj', (object,), {
                        'left': int(x_min),
                        'top': int(y_min),
                        'width': int(w),
                        'height': int(h)
                    })
                    
                    detected_codes.append({
                        'data': data,
                        'type': 'QRCODE',
                        'rect': rect_obj,
                        'polygon': polygon
                    })
                    break
        except Exception as e:
            print(f"Error in preprocessing: {e}")
    
    return detected_codes


def process_image(image_path):
    """Process a single image file for QR codes"""
    img = cv2.imread(image_path)
    if img is None:
        print(f"ERROR: Could not read image file: {image_path}")
        return
    
    detected_codes = decode_qr_codes(img)
    
    if not detected_codes:
        print(f"No QR codes found in {image_path}")
        return
    
    print(f"Found {len(detected_codes)} QR code(s) in {image_path}:")
    for i, code in enumerate(detected_codes):
        print(f"  {i+1}. Type: {code['type']}, Data: {code['data']}")
        
    # Display the image with detections
    display_img = img.copy()
    
    # Draw QR codes on the image
    for code in detected_codes:
        # Draw polygon around the QR code
        pts_array = np.array([code['polygon']], np.int32)
        cv2.polylines(display_img, [pts_array], True, (0, 255, 0), 2)
        
        # Display data
        rect = code['rect']
        cv2.putText(display_img, str(code['data']), 
                   (rect.left, rect.top - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Show the image
    cv2.imshow("QR Code Detection", display_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def process_directory(directory_path):
    """Process all images in a directory for QR codes"""
    if not os.path.isdir(directory_path):
        print(f"ERROR: {directory_path} is not a valid directory")
        return
        
    supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')
    processed = 0
    
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(supported_extensions):
            image_path = os.path.join(directory_path, filename)
            print(f"\nProcessing {filename}...")
            process_image(image_path)
            processed += 1
    
    if processed == 0:
        print(f"No supported image files found in {directory_path}")


def start_webcam_scanner():
    """Start a webcam-based QR code scanner"""
    print("Starting webcam QR code scanner...")
    print("Press 'q' to quit")
    
    # Try to open webcam
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("ERROR: Could not open webcam. Please check your camera connection.")
        return False
    
    # Set camera properties (width and height)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    last_detection_time = 0
    detection_cooldown = 0.5  # seconds between detections to avoid duplicates
    
    while True:
        ret, frame = cam.read()
        if not ret:
            print("ERROR: Failed to grab frame from camera")
            break
        
        # Make a copy of the frame for drawing
        display_frame = frame.copy()
        
        # Detect QR codes
        current_time = time.time()
        if current_time - last_detection_time >= detection_cooldown:
            detected_codes = decode_qr_codes(frame)
            
            if detected_codes:
                last_detection_time = current_time
                
                # Process each detected code
                for code in detected_codes:
                    print(f"QR Code detected: {code['data']}")
                    
                    # Draw polygon around the QR code
                    pts_array = np.array([code['polygon']], np.int32)
                    cv2.polylines(display_frame, [pts_array], True, (0, 255, 0), 2)
                    
                    # Display data
                    rect = code['rect']
                    cv2.putText(display_frame, str(code['data']), 
                               (rect.left, rect.top - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Display the frame
        cv2.imshow("QR Code Scanner", display_frame)
        
        # Check for key press to exit
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
    
    # Release resources
    cam.release()
    cv2.destroyAllWindows()
    return True


def main():
    parser = argparse.ArgumentParser(description="QR Code Scanner using OpenCV")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-f", "--file", help="Path to a single image file to scan")
    group.add_argument("-d", "--directory", help="Path to a directory of images to scan")
    group.add_argument("-w", "--webcam", action="store_true", help="Use webcam for real-time scanning")
    
    args = parser.parse_args()
    
    if args.file:
        process_image(args.file)
    elif args.directory:
        process_directory(args.directory)
    elif args.webcam:
        start_webcam_scanner()
    else:
        # Default to webcam if no arguments provided
        if not start_webcam_scanner():
            print("\nFallback to directory scanning mode.")
            print("Enter a directory path to scan for QR codes:")
            directory = input("> ")
            if os.path.isdir(directory):
                process_directory(directory)
            else:
                print(f"ERROR: {directory} is not a valid directory")


if __name__ == "__main__":
    main()
