import argparse
import os
import cv2
import numpy as np # OpenCV requires numpy

# Disable OpenCV debug output
from sys import stdout
stdout.flush()

# List of common image file extensions to process
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

def find_and_decode_qrs(image_path):
    """
    Opens a single image file, finds QR codes, and decodes them.

    Args:
        image_path (str): The path to the image file.

    Returns:
        list: A list of decoded data strings found in the QR codes.
              Returns an empty list if no QR codes are found or an error occurs.
    """
    decoded_data_list = []
    try:
        # Read the image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            print(f"    ERROR: Could not read image file at '{image_path}'.")
            return []

        # Try different QR code detection methods
        found_codes = []
        
        # Method 1: Direct QR code detection
        direct_results = detect_qr_direct(img)
        if direct_results:
            found_codes.extend(direct_results)
            
        # Method 2: If no QR codes found, try with image preprocessing
        if not found_codes:
            print(f"    INFO: Trying with image preprocessing...")
            preprocessed_results = detect_qr_with_preprocessing(img)
            if preprocessed_results:
                found_codes.extend(preprocessed_results)
        
        # Method 3: Try with localized region detection
        if not found_codes:
            print(f"    INFO: Trying with region detection...")
            region_results = detect_qr_by_regions(img)
            if region_results:
                found_codes.extend(region_results)
                
        if not found_codes:
            print(f"    INFO: No QR codes found in this image.")
            return []
        
        print(f"    INFO: Found {len(found_codes)} QR code(s):")
        for i, (qr_type, data) in enumerate(found_codes):
            print(f"      {i+1}. Type: {qr_type}, Decoded Data: {data}")
            decoded_data_list.append(data)
            
        return decoded_data_list

    except FileNotFoundError:
        print(f"    ERROR: Image file not found at '{image_path}'.")
        return []
    except Exception as e:
        # Catch potential errors
        print(f"    ERROR: Could not process image '{os.path.basename(image_path)}': {e}")
        return []

def detect_qr_direct(img):
    """
    Detects QR codes directly using OpenCV's QRCodeDetector.
    
    Args:
        img: OpenCV image object
        
    Returns:
        list: List of tuples (qr_type, data)
    """
    results = []
    try:
        # Initialize the QRCode detector
        qr_detector = cv2.QRCodeDetector()
        
        # Try multi-QR code detection first
        retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(img)
        
        if retval:
            # Filter out empty strings
            valid_codes = [("QR Code", info) for info in decoded_info if info]
            if valid_codes:
                return valid_codes
                
        # Try single QR code detection as fallback
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(img)
        if data:
            return [("QR Code", data)]  
    except Exception as e:
        print(f"    WARNING: QR code detection error: {e}")
    
    return results

def detect_qr_with_preprocessing(img):
    """
    Detects QR codes using different image preprocessing techniques.
    
    Args:
        img: OpenCV image object
        
    Returns:
        list: List of tuples (qr_type, data)
    """
    results = []
    qr_detector = cv2.QRCodeDetector()
    
    try:
        # Convert to grayscale if not already
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Try different preprocessing techniques
        
        # 1. Try with inverted image (sometimes QR codes are inverted)
        inverted = cv2.bitwise_not(gray)
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(inverted)
        if data:
            results.append(("QR Code (Inverted)", data))
        
        # 2. Try with blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(blurred)
        if data:
            results.append(("QR Code (Blurred)", data))
        
        # 3. Try with sharpening
        kernel = np.array([[-1,-1,-1], 
                         [-1, 9,-1],
                         [-1,-1,-1]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(sharpened)
        if data:
            results.append(("QR Code (Sharpened)", data))
        
        # 4. Try with various threshold techniques
        for threshold_type in [cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV]:
            for threshold_value in [100, 150, 200]:
                _, binary = cv2.threshold(gray, threshold_value, 255, threshold_type)
                data, bbox, straight_qrcode = qr_detector.detectAndDecode(binary)
                if data:
                    results.append(("QR Code (Binary)", data))
                    break
        
        # 5. Try with adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY, 11, 2)
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(adaptive_thresh)
        if data:
            results.append(("QR Code (Adaptive)", data))
            
        # 6. Try with histogram equalization for better contrast
        equalized = cv2.equalizeHist(gray)
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(equalized)
        if data:
            results.append(("QR Code (Equalized)", data))
            
    except Exception as e:
        print(f"    WARNING: QR code preprocessing error: {e}")
    
    return results

def detect_qr_by_regions(img):
    """
    Detects QR codes by analyzing specific regions of the image.
    
    Args:
        img: OpenCV image object
        
    Returns:
        list: List of tuples (qr_type, data)
    """
    results = []
    qr_detector = cv2.QRCodeDetector()
    
    try:
        # Get image dimensions
        height, width = img.shape[:2]
        
        # Convert to grayscale if not already
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Find potential QR code regions
        # 1. Using edge detection and contours
        edges = cv2.Canny(gray, 50, 200)
        
        # Dilate the edges to connect broken lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(edges, kernel)
        
        # Find contours in the edge image
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        potential_regions = []
        
        # Process each contour to find square-like shapes (potential QR codes)
        for contour in contours:
            # Approximate the contour to a polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
            
            # QR codes are typically square-ish with 4 corners
            if len(approx) >= 4 and len(approx) <= 8:
                x, y, w, h = cv2.boundingRect(approx)
                
                # Check for reasonable size and aspect ratio for a QR code
                area = w * h
                if area < 400:  # Too small
                    continue
                    
                aspect_ratio = float(w) / h
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:  # Too stretched
                    continue
                
                # Add some padding to include full QR code
                padding = max(10, int(min(w, h) * 0.1))
                x_padded = max(0, x - padding)
                y_padded = max(0, y - padding)
                w_padded = min(width - x_padded, w + 2*padding)
                h_padded = min(height - y_padded, h + 2*padding)
                
                # Extract the region
                region = img[y_padded:y_padded+h_padded, x_padded:x_padded+w_padded]
                
                if region.size == 0 or region.shape[0] == 0 or region.shape[1] == 0:
                    continue
                    
                potential_regions.append(region)
        
        # 2. Also try a grid-based approach for smaller or partial QR codes
        grid_size = 4  # 4x4 grid
        cell_height = height // grid_size
        cell_width = width // grid_size
        
        for i in range(grid_size):
            for j in range(grid_size):
                # Get cell coordinates
                start_y = i * cell_height
                start_x = j * cell_width
                
                # Extract grid cell with overlap from adjacent cells
                overlap = max(10, int(min(cell_height, cell_width) * 0.2))
                y1 = max(0, start_y - overlap)
                x1 = max(0, start_x - overlap)
                y2 = min(height, start_y + cell_height + overlap)
                x2 = min(width, start_x + cell_width + overlap)
                
                cell = img[y1:y2, x1:x2]
                potential_regions.append(cell)
        
        # Process each potential region
        for region in potential_regions:
            try:
                # Try direct QR code detection
                data, bbox, straight_qrcode = qr_detector.detectAndDecode(region)
                if data:
                    results.append(("QR Code (Region)", data))
                    continue
                    
                # If direct detection fails, try with preprocessing
                # Convert to grayscale if not already
                if len(region.shape) == 3:
                    region_gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                else:
                    region_gray = region
                
                # Try with binary thresholding
                _, binary = cv2.threshold(region_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                data, bbox, straight_qrcode = qr_detector.detectAndDecode(binary)
                if data:
                    results.append(("QR Code (Region-Binary)", data))
                    continue
                    
                # Try with enhanced contrast
                enhanced = cv2.equalizeHist(region_gray)
                data, bbox, straight_qrcode = qr_detector.detectAndDecode(enhanced)
                if data:
                    results.append(("QR Code (Region-Enhanced)", data))
            except Exception as e:
                continue  # Skip this region if there's an error
    
    except Exception as e:
        print(f"    WARNING: Region detection error: {e}")
    
    return results

def process_directory(directory_path):
    """
    Scans a directory for image files and attempts to decode QR codes in each.

    Args:
        directory_path (str): The path to the directory containing image files.

    Returns:
        dict: A dictionary where keys are image file paths and values are lists
              of decoded strings found in that image. Returns an empty dict if
              the directory is invalid or contains no processable images.
    """
    all_results = {}
    found_images = 0

    if not os.path.isdir(directory_path):
        print(f"ERROR: Provided path '{directory_path}' is not a valid directory.")
        return {}

    print(f"Scanning directory: '{directory_path}'...")

    # Walk through the directory
    for filename in os.listdir(directory_path):
        # Check if the file has a supported image extension (case-insensitive)
        if filename.lower().endswith(SUPPORTED_EXTENSIONS):
            full_path = os.path.join(directory_path, filename)

            # Ensure it's actually a file (not a subdirectory with a matching extension name)
            if os.path.isfile(full_path):
                found_images += 1
                print(f"\n--- Processing image: {filename} ---")
                decoded_values = find_and_decode_qrs(full_path)
                if decoded_values: # Only add to results if something was found
                    all_results[full_path] = decoded_values
                else:
                    # Keep track of files processed even if nothing was decoded
                    all_results[full_path] = [] # Represented as an empty list
            else:
                print(f"Skipping non-file entry: {filename}")
        # else:
            # Optional: print skipped files
            # print(f"Skipping non-image file: {filename}")


    if found_images == 0:
        print(f"\nINFO: No supported image files ({', '.join(SUPPORTED_EXTENSIONS)}) found in the directory.")
    else:
        print(f"\n--- Scan Complete ---")
        print(f"Processed {found_images} image file(s).")

    return all_results

if __name__ == "__main__":
    # Set up argument parser for command-line usage
    parser = argparse.ArgumentParser(
        description="Scan a directory for image files, find QR codes (and other barcodes) within them, and print decoded data."
    )
    parser.add_argument(
        "directory_path", # Positional argument
        help="Path to the directory containing the image files to scan."
    )

    # Parse arguments from the command line
    args = parser.parse_args()

    # Call the directory processing function
    results = process_directory(args.directory_path)

    # Optional: Print a summary of all found codes at the end
    print("\n--- Summary ---")
    total_codes_found = 0
    files_with_codes = 0
    if not results:
        print("No QR codes or barcodes were decoded in any image.")
    else:
        for filepath, decoded_list in results.items():
            filename = os.path.basename(filepath)
            if decoded_list:
                files_with_codes += 1
                total_codes_found += len(decoded_list)
                print(f"  - {filename}: Found {len(decoded_list)} code(s)")
                # for data in decoded_list: # Uncomment to list data again in summary
                #    print(f"    - {data}")
            # else: # Uncomment to explicitly mention files with no codes found
            #    print(f"  - {filename}: No codes found")

        print(f"\nFound a total of {total_codes_found} code(s) across {files_with_codes} file(s).")