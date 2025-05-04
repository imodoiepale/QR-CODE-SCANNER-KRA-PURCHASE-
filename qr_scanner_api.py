from flask import Flask, request, jsonify, send_from_directory
import cv2
import os
import numpy as np
import tempfile
import logging
import base64
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

# Create a temporary directory for storing uploaded images
TEMP_DIR = tempfile.gettempdir()


def scan_qr_code_from_image(image_path):
    """
    Scan an image for QR codes and extract data using OpenCV's QR code detector.
    
    Args:
        image_path (str): Path to the image containing QR code
        
    Returns:
        list: List of dictionaries containing decoded data and QR code information
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        
        if img is None:
            logger.error(f"Could not read image at {image_path}")
            return []
        
        # Create a QR code detector
        qr_detector = cv2.QRCodeDetector()
        
        # Detect and decode QR codes
        data, points, straight_qrcode = qr_detector.detectAndDecodeMulti(img)
        
        # If no QR code is detected, points will be None
        if points is None:
            logger.info(f"No QR codes found in {image_path}")
            return []
        
        results = []
        
        # Process each detected QR code
        for i, qr_data in enumerate(data):
            if not qr_data:  # Skip empty results
                continue
                
            qr_points = points[i].astype(int)
            
            # Calculate the bounding rectangle
            x_min, y_min = np.min(qr_points[:, 0]), np.min(qr_points[:, 1])
            x_max, y_max = np.max(qr_points[:, 0]), np.max(qr_points[:, 1])
            width, height = x_max - x_min, y_max - y_min
            
            # Convert the polygon points to dictionary format
            polygon_points = []
            for point in qr_points:
                polygon_points.append({"x": int(point[0]), "y": int(point[1])})
            
            # Add result data
            results.append({
                "data": qr_data,
                "type": "QRCODE",  # OpenCV doesn't differentiate QR code types
                "rect": {
                    "left": int(x_min),
                    "top": int(y_min),
                    "width": int(width),
                    "height": int(height)
                },
                "polygon": polygon_points
            })
            
            logger.info(f"Detected QR code: Data: {qr_data}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing {image_path}: {str(e)}")
        return []


def scan_qr_code_from_bytes(image_bytes):
    """
    Scan an image from bytes for QR codes using OpenCV's QR code detector.
    
    Args:
        image_bytes (bytes): Raw image data
        
    Returns:
        list: List of dictionaries containing decoded data and QR code information
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Could not decode image from bytes")
            return []
        
        # Create a QR code detector
        qr_detector = cv2.QRCodeDetector()
        
        # Detect and decode QR codes
        data, points, straight_qrcode = qr_detector.detectAndDecodeMulti(img)
        
        # If no QR code is detected, points will be None
        if points is None:
            logger.info("No QR codes found in image")
            return []
        
        results = []
        
        # Process each detected QR code
        for i, qr_data in enumerate(data):
            if not qr_data:  # Skip empty results
                continue
                
            qr_points = points[i].astype(int)
            
            # Calculate the bounding rectangle
            x_min, y_min = np.min(qr_points[:, 0]), np.min(qr_points[:, 1])
            x_max, y_max = np.max(qr_points[:, 0]), np.max(qr_points[:, 1])
            width, height = x_max - x_min, y_max - y_min
            
            # Convert the polygon points to dictionary format
            polygon_points = []
            for point in qr_points:
                polygon_points.append({"x": int(point[0]), "y": int(point[1])})
            
            # Add result data
            results.append({
                "data": qr_data,
                "type": "QRCODE",  # OpenCV doesn't differentiate QR code types
                "rect": {
                    "left": int(x_min),
                    "top": int(y_min),
                    "width": int(width),
                    "height": int(height)
                },
                "polygon": polygon_points
            })
            
            logger.info(f"Detected QR code: Data: {qr_data}")
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing image bytes: {str(e)}")
        return []


@app.route('/api/scan', methods=['POST'])
def scan_qr_code_endpoint():
    """
    API endpoint to scan an uploaded image for QR codes.
    
    Accepts files via multipart/form-data with a 'file' field.
    """
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file part in the request"
            }), 400
        
        file = request.files['file']
        
        # If user does not select file, browser might submit an empty part
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No selected file"
            }), 400
        
        # Check if the file is an image
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
        if '.' not in file.filename or file.filename.split('.')[-1].lower() not in allowed_extensions:
            return jsonify({
                "status": "error",
                "message": "File not allowed. Supported formats: png, jpg, jpeg, gif, bmp"
            }), 400
        
        # Save the file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(TEMP_DIR, filename)
        file.save(temp_path)
        
        # Process the image
        results = scan_qr_code_from_image(temp_path)
        
        # Remove the temporary file
        os.remove(temp_path)
        
        # Return the results
        return jsonify({
            "status": "success",
            "message": f"Found {len(results)} QR code(s)" if results else "No QR codes found",
            "count": len(results),
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error in scan_qr_code_endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500


@app.route('/api/scan-base64', methods=['POST'])
def scan_qr_code_base64_endpoint():
    """
    API endpoint to scan a base64 encoded image for QR codes.
    
    Accepts JSON with a 'base64_image' field containing the base64 encoded image.
    """
    try:
        # Get the JSON data
        data = request.get_json()
        
        if not data or 'base64_image' not in data:
            return jsonify({
                "status": "error",
                "message": "No base64_image field in the request"
            }), 400
        
        # Get the base64 encoded image
        base64_image = data['base64_image']
        
        # Remove the data URL prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Decode the base64 image
        image_bytes = base64.b64decode(base64_image)
        
        # Process the image
        results = scan_qr_code_from_bytes(image_bytes)
        
        # Return the results
        return jsonify({
            "status": "success",
            "message": f"Found {len(results)} QR code(s)" if results else "No QR codes found",
            "count": len(results),
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error in scan_qr_code_base64_endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "message": "QR Code Scanner API is running"
    })

@app.route('/')
def serve_index():
    """Serve the index.html file"""
    return send_from_directory('.', 'index.html')


# Create ASGI application for use with Uvicorn
from asgiref.wsgi import WsgiToAsgiApplication
asgi_app = WsgiToAsgiApplication(app)

# Main entry point
if __name__ == "__main__":
    print("Starting QR Code Scanner API on http://127.0.0.1:8080")
    print("Web interface available at http://127.0.0.1:8080")
    print("To use Uvicorn instead, run: uvicorn qr_scanner_api:asgi_app --host 127.0.0.1 --port 8080")
    app.run(host="127.0.0.1", port=8080, debug=True)
