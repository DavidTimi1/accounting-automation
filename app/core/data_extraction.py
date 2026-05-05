import re
from app.core.ai_client import ai_extract_invoice_data

MODES = ("AI", "NORMAL")

# ~4 characters per token is a safe rule of thumb.
TOKEN_LIMIT_CHARS = 32000  # Approx 8000 tokens

class InvoiceDataExtractor:
    def __init__(self, mode = "NORMAL", month=None, folder_path=None):
        self.mode = mode
        self.folder_path = folder_path
        self.month = month

    def run(self, all_results, callback):
        if self.mode == "AI":
            print("\nUsing AI for extraction...\n")
            self.ai_mode(all_results, callback)
        else:
            print("Using normal extraction...\n")
            self.normal_mode(all_results, callback)
        

    def normal_mode(self, all_results, callback):
        for result in all_results:
            filename = result['file']
            text = result['text']
            
            if "error" in result:
                print(f"❌ Skipped {filename} due to OCR error: {result['error']}")
                continue
            
            data = extract_invoice_data(text, filename, self.month)    
            callback(data)

    def ai_mode(self, all_results, callback):        
        current_batch_text = ''
        batches = []

        for result in all_results:
            if "error" in result:
                print(f"❌ Skipped {result['file']} due to OCR error: {result['error']}")
                continue
                
            invoice_entry = f"\n\nFilename: {result['file']}\n{result['text']}"
            
            # If adding this invoice exceeds the limit, save the current batch and start new
            if len(current_batch_text) + len(invoice_entry) > TOKEN_LIMIT_CHARS:
                if current_batch_text:
                    batches.append(current_batch_text)
                current_batch_text = invoice_entry
            else:
                current_batch_text += invoice_entry

        # Add the final remaining batch
        if current_batch_text:
            batches.append(current_batch_text)

        if not batches:
            print("No data to extract")
            return

        all_results_index = 0
        # Process each batch sequentially
        for i, batch in enumerate(batches):
            print(f"Processing batch {i+1}/{len(batches)}...")
            
            # Ensure your ai_extract_invoice_data function sets max_tokens (e.g., 2000)
            response = ai_extract_invoice_data(batch)
            
            if response is None:
                print(f"❌ AI Error: Batch {i+1} failed")
                continue

            # Process the list of extracted items
            for j, item in enumerate(response):
                item_data = item | {
                    "filename": all_results[all_results_index]['file'] # re-inforce extact filename
                }

                all_results_index += 1
                callback(item_data)

        

def extract_invoice_data(text, filename, month):
    referrer = extract_referrer_from_filename(filename)
    
    # 1. Client Name Extraction
    client_name = "Unknown"
    match_type = None
    # Match the block between Invoice No and Date\
    pattern = r"ATT:.*?\|.*?\n(.*?)(?=\s*Date\s*\|)"

    client_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if client_match:
        client_name = client_match.group(1).strip().replace('\n', ' ')
        match_type = "1"
    else:
        # Fallback for different layouts: look after ATT: Invoice No
        fallback_client = re.search(r"ATT:\s*(.*?)\s*(?=\|)", text, re.IGNORECASE)
        if fallback_client:
            client_name = fallback_client.group(1).strip().replace('\n', ' ')
            match_type = "2"
        else: 
            client_name = extract_client_from_filename(filename)
            match_type = "3"

    # 2. Venue Extraction
    venue_match = re.search(r"VENUE:\s*(.*?)(?:\n|DATE:|$)", text, re.IGNORECASE)
    venue = venue_match.group(1).strip() if venue_match else "Not Specified"

    # 3. Date from Filename
    date_pattern = r"(\d{1,2}(?:st|nd|rd|th)?(?:\s*[-&]\s*\d{1,2}(?:st|nd|rd|th)?)?\s+" + month + r")"
    date_match = re.search(date_pattern, filename, re.IGNORECASE)
    extracted_date = date_match.group(1).strip() if date_match else "Unknown Date"

    # 4. VAT Amount (Careful to avoid VAT NO / TIN)
    # We look specifically for "VAT(7.5%)" or "VAT" followed by a newline or small space and a number
    vat = 0.0
    vat_match = re.search(r"VAT\s*\(?7\.5%\)?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
    if vat_match:
        vat = clean_num(vat_match.group(1))

    # Amounts
    # Logistics: Looks for "LOGISTICS" or cost for hire then a number
    logistics_match = re.search(r"LOGISTICS\s*([\d,.]+)", text, re.IGNORECASE)
    cost_for_hire_match = re.search(r"COST FOR HIRE\s*([\d,.]+)", text, re.IGNORECASE)
    if logistics_match:
        logistics = clean_num(logistics_match.group(1))
    elif cost_for_hire_match:
        logistics = clean_num(cost_for_hire_match.group(1))
    else:
        logistics = 0.0

# 6. Discount
    discount = 0.0
    # Capture numbers following "DISCOUNT" including the minus sign
    disc_match = re.search(r"DISCOUNT\s*-?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
    if disc_match:
        discount = clean_num(disc_match.group(1))

    # 7. Total Cost vs Amount Payable
    # Total Cost is usually the sum before the discount is applied or the final subtotal
    total_cost_match = re.search(r"TOTAL COST\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
    total_cost = clean_num(total_cost_match.group(1)) if total_cost_match else 0.0

    # Amount Payable is the final check/cash required
    payable_match = re.search(r"AMOUNT\s*(?:PAYABLE)?\s*N?([\d,]+\.\d{2})", text, re.IGNORECASE)
    amount_payable = clean_num(payable_match.group(1)) if payable_match else 0.0

    # If Total Cost wasn't found but Amount Payable exists, and there's no discount, they are the same
    if total_cost == 0 and amount_payable > 0:
        total_cost = amount_payable

    # --- NEW REMARK LOGIC ---
    remark = extra_col = ""
    
    if amount_payable == 0:
        remark = "FREE"
    
    elif discount > 0:
        # This creates the format: "10000.0 Discount, TOTAL: 10000.0"
        remark = f"discount given/TODO"
        extra_col = f"{discount:,.2f} Discount, TOTAL: {total_cost:,.2f}"

    # Prepare metadata for the ExcelHandler (we ignore 'remark' here)
    extracted_data = {
        "filename": filename,
        "client_match": match_type,
        "date": extracted_date,
        "venue": venue,
        "client_name": client_name,
        "amount_payable": amount_payable,
        "total_cost": total_cost,
        "logistics": logistics,
        "vat": vat,
        "discount": discount,
        "referrer": referrer,
        "remark": remark,
        "extra": extra_col
    }
    
    return extracted_data


def clean_num(val):
    if not val: return 0.0
    # Remove commas and handle currency symbols
    cleaned = re.sub(r"[^\d.]", "", val.replace(",", ""))
    try:
        return float(cleaned)
    except:
        return 0.0
    
    
def extract_client_from_filename(filename):
    clean_name = filename.split(".")[-2]
    pattern = r"INVOICE FOR\s+(.*?)(?=\s+\d|$)"
    match = re.search(pattern, clean_name, re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    elif "-" in clean_name:
        parts = clean_name.split("-")
        return parts[1].strip()
        
    return None

def extract_referrer_from_filename(filename):
    # first 3 letters of filename
    return filename[:3].upper()