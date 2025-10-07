#!/usr/bin/env python3
"""
Image Text Extractor
Extracts text from images in a given directory using Tesseract OCR.

Requirements:
    pip install pytesseract pillow
    
System Requirements:
    - Tesseract OCR must be installed on your system
    - Ubuntu/Debian: sudo apt-get install tesseract-ocr
    - macOS: brew install tesseract
    - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
"""

import os
import sys
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
except ImportError as e:
    print("Error: Required libraries not installed.")
    print("\nPlease install required packages:")
    print("  pip install pytesseract pillow")
    print("\nAlso ensure Tesseract OCR is installed on your system:")
    print("  Ubuntu/Debian: sudo apt-get install tesseract-ocr")
    print("  macOS: brew install tesseract")
    print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    sys.exit(1)


def extract_text_from_image(image_path):
    """
    Extract text from an image file using Tesseract OCR.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Extracted text as a string
    """
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        text = text.strip()
        
        if not text:
            return "[No text detected in image]"
        
        return text
    
    except pytesseract.TesseractNotFoundError:
        return "Error: Tesseract OCR is not installed or not in PATH"
    except Exception as e:
        return f"Error extracting text: {str(e)}"


def is_image_file(filename):
    """Check if a file is an image based on extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
    return Path(filename).suffix.lower() in image_extensions


def process_directory(directory_path):
    """
    Process all image files in a directory.
    
    Args:
        directory_path: Path to the directory containing images
    """
    path = Path(directory_path)
    
    if not path.exists():
        print(f"Error: Path '{directory_path}' does not exist.")
        return
    
    if not path.is_dir():
        print(f"Error: '{directory_path}' is not a directory.")
        return
    
    # Find all image files
    image_files = [f for f in path.iterdir() if f.is_file() and is_image_file(f.name)]
    
    if not image_files:
        print(f"No image files found in '{directory_path}'")
        return
    
    for image_file in sorted(image_files):
        print(f"\n\033[1m{image_file.name}\033[0m\n")
        text = extract_text_from_image(str(image_file))
        print(text)
        print("\n" + "=" * 70)


def process_single_file(file_path):
    """
    Process a single image file.
    
    Args:
        file_path: Path to the image file
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        return
    
    if not path.is_file():
        print(f"Error: '{file_path}' is not a file.")
        return
    
    if not is_image_file(path.name):
        print(f"Error: '{file_path}' does not appear to be an image file.")
        print(f"Supported formats: jpg, jpeg, png, gif, bmp, tiff, webp")
        return
    
    print(f"\n\033[1m{path.name}\033[0m\n")
    text = extract_text_from_image(str(path))
    print(text)
    print("\n" + "=" * 70)


def main():
    """Main function to handle command-line interface."""
    if len(sys.argv) > 1:
        # Path provided as command-line argument
        target_path = sys.argv[1]
    else:
        # Interactive mode
        target_path = input("Enter source: ").strip()
    
    if not target_path:
        print("Error: No path provided.")
        return
    
    # Expand user path (handles ~)
    target_path = os.path.expanduser(target_path)
    path = Path(target_path)
    
    if path.is_dir():
        process_directory(target_path)
    elif path.is_file():
        process_single_file(target_path)
    else:
        print(f"Error: '{target_path}' is not a valid file or directory.")


if __name__ == "__main__":
    main()
