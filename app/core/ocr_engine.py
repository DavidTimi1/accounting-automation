import os
import sys
import platform
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from thefuzz import fuzz
from concurrent.futures import ProcessPoolExecutor
import pytesseract
from pdf2image import convert_from_path

# --- UTILITY FOR BUNDLED BINARIES ---
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- OCR ENGINE (PARALLEL) ---
class OCREngine:
    def __init__(self, max_workers=None):
        self.current_os = platform.system()
        self.max_workers = max_workers or os.cpu_count()
        
        # Configure Paths based on OS
        if self.current_os == "Windows":
            self.tess_path = get_resource_path("bin/Tesseract-OCR/tesseract.exe")
            self.poppler_path = get_resource_path("bin/poppler/bin")
            pytesseract.pytesseract.tesseract_cmd = self.tess_path
            
        else:
            # Ubuntu/Linux defaults
            self.tess_path = "/usr/bin/tesseract"
            self.poppler_path = None

    
    def get_text_from_pdf(self, pdf_path, dpi=200): # Lower DPI for speed if text is clear
        try:
            # ProcessPoolExecutor is better for CPU-heavy tasks like OCR
            pages = convert_from_path(pdf_path, dpi=dpi)
            full_text = ""
            for page in pages:
                full_text += pytesseract.image_to_string(page)
            return {"file": os.path.basename(pdf_path), "text": full_text}
        except Exception as e:
            return {"file": os.path.basename(pdf_path), "error": str(e)}

    def process_multiple_files(self, file_paths):
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # map distributes the files across your CPU cores
            results = list(executor.map(self.get_text_from_pdf, file_paths))
        return results