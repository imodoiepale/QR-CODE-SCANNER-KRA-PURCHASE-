# QR Code Scanner

A Python utility for scanning QR codes from images and extracting URLs.

## Features

- Scan a single image for QR codes
- Scan all images in a directory
- Extract URLs and text data from QR codes
- Display visual feedback with highlighted QR code locations
- Interactive mode for easier usage

## Installation

1. Make sure you have Python installed (3.6 or newer recommended)

2. Install the required dependencies:

```
pip install -r requirements.txt
```

Note: On Windows, you might need to install the `zbar` shared library separately if `pyzbar` installation fails.

## Usage

### Command Line

Scan a single image:
```
python qr_scanner.py -i path/to/image.jpg
```

Scan all images in a directory:
```
python qr_scanner.py -d path/to/directory
```

### Interactive Mode

Simply run the script without arguments:
```
python qr_scanner.py
```

Follow the prompts to scan a single image or a directory of images.

## Supported Image Formats

- JPG/JPEG
- PNG
- BMP
- GIF

## Notes

- The program will display each image with detected QR codes highlighted
- Press any key to close the image window and continue processing
- For batch directory scanning, results will be printed to the console
