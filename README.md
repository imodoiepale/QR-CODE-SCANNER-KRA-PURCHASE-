# QR Code Scanner API

A web-based API service for scanning QR codes from uploaded images.

## Features

- Scan QR codes from uploaded images
- Scan QR codes using your device camera
- RESTful API endpoints
- Web interface for easy testing
- Extracts QR code data, type, position, and quality
- Supports multiple QR codes in a single image

## API Endpoints

### 1. `POST /api/scan`

Upload and scan an image file for QR codes.

**Request:**
- `Content-Type`: multipart/form-data
- Form field: `file` - The image file to scan

**Response:**
```json
{
  "status": "success",
  "message": "Found 1 QR code(s)",
  "count": 1,
  "results": [
    {
      "data": "https://example.com",
      "type": "QRCODE",
      "rect": {
        "left": 10,
        "top": 10,
        "width": 200,
        "height": 200
      },
      "polygon": [
        {"x": 10, "y": 10},
        {"x": 210, "y": 10},
        {"x": 210, "y": 210},
        {"x": 10, "y": 210}
      ],
      "orientation": "UP",
      "quality": 85
    }
  ]
}
```

### 2. `POST /api/scan-base64`

Scan a base64-encoded image for QR codes.

**Request:**
- `Content-Type`: application/json
- Body: `{ "base64_image": "base64EncodedImageString" }`

**Response:**
Same structure as `/api/scan`

### 3. `GET /api/health`

Check the API status.

**Response:**
```json
{
  "status": "online",
  "message": "QR Code Scanner API is running"
}
```

## Installation

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the API server:
```
python qr_scanner_api.py
```

3. The server will start at http://localhost:8080

## Web Interface

A demo interface is available at http://localhost:8080/index.html which provides:

- File upload option for scanning QR codes
- Camera integration for scanning QR codes in real-time
- Result display with formatted QR code data

## Libraries Used

- Flask - Web framework
- OpenCV - Image processing
- pyzbar - QR code and barcode scanning
- NumPy - Array manipulation for image data
- Werkzeug - File handling and security

## Requirements

See `requirements.txt` for a full list of dependencies.

## Notes

- The API limits file uploads to 16MB
- Supported image formats: PNG, JPG, JPEG, GIF, BMP
- For production use, consider adding authentication
- The temporary directory is used for file processing
