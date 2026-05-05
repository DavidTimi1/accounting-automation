from app.core.utils import log_info
from app.core.data_extraction import InvoiceDataExtractor
import os
import argparse
import datetime
import tkinter as tk
import shutil
from tkinter import filedialog
from app.core.ocr_engine import OCREngine
from app.core.excel_handler import ExcelHandler
from dotenv import load_dotenv

load_dotenv()

CONCURRENT_RATE = 4

def run_automation(period=None, folder_path=None):
    if period is None:
        period = datetime.datetime.now().strftime("%b %y")

    else:
        period = str(period)

    month = period.split(" ")[0].lower()
    print(f"Using period: {period}")
        
    # Setup
    ocr = OCREngine()
    
    if folder_path is None:
        # Use tkinter to select the folder containing invoices
        root = tk.Tk()
        root.withdraw() # Hide the main tk window
        folder_path = filedialog.askdirectory(title="Select Folder with Invoices")
    
    if not folder_path:
        print("No folder selected. Exiting.")
        return
        
    print(f"Selected folder: {folder_path}")    
    
    pdf_files = [
        os.path.join(folder_path, f) 
        for f in os.listdir(folder_path) 
        if f.lower().endswith(".pdf")
    ]
    
    all_extracted_texts = []

    print("Extracting text from PDFs...")
    batches = (len(pdf_files) // CONCURRENT_RATE) + 1
    for i in range(batches):
        print(f"Processing batch {i+1} of {batches}")
        offset = i * CONCURRENT_RATE
        batch = pdf_files[offset: offset + CONCURRENT_RATE]
        all_extracted_texts.extend(ocr.process_multiple_files(batch))
    print("All text extracted 💫\n")
    
    # Process each PDF in the folder
    processed_folder = os.path.join(folder_path, "Processed")
    flagged_folder = os.path.join(folder_path, "Flagged_Discrepancies")
    os.makedirs(processed_folder, exist_ok=True)
    os.makedirs(flagged_folder, exist_ok=True)

    discrepancies = []
    unresolved = []

    excel = ExcelHandler("data/templates/report.xlsx")


    def process_result(data, folder_path, period):
        filename = data['filename']
        file_path = os.path.join(folder_path, filename)

        # Update Excel & Verify Discrepancies
        try:
            status, msg = excel.process_invoice(data, provided_sheet_name=period)

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            unresolved.append((filename,msg))
            return
        
        if status in ["MATCHED", "CREATED"]:
            dest_path = os.path.join(processed_folder, filename)
            shutil.move(file_path, dest_path)
            
        elif status == "DISCREPANCY":
            dest_path = os.path.join(flagged_folder, filename) # keep original name for review
            discrepancies.append((filename,msg))
            shutil.move(file_path, dest_path)

        else:
            unresolved.append((filename,msg))


    def callback(data):
        process_result(data, folder_path, period)


    data_extractor = InvoiceDataExtractor('AI', month, folder_path)
    data_extractor.run(all_extracted_texts, callback)

    if len(discrepancies) > 0:
        print("\nThe following files had discrepancies:")
        log_json = [{"file": filename, "message": msg} for filename,msg in unresolved]
        log_info(log_json, "discrepancies")

    if len(unresolved) > 0:
        print("\nThe following files could not be processed:")
        log_json = [{"file": filename, "message": msg} for filename,msg in unresolved]
        log_info(log_json, "unresolved")
        
        
    print("\nDone processing folder!")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Account Logging App")
    parser.add_argument("--period", help="Period to use for the sheet name (e.g., 'Apr 26'). Defaults to current month and year.", default=None)
    parser.add_argument("--folder", help="Path to the folder containing invoices.", default=None)
    args = parser.parse_args()
    
    run_automation(period=args.period, folder_path=args.folder)