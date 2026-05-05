from app.core.utils import log_info
import os
import pandas as pd
from openpyxl import load_workbook
from thefuzz import fuzz

required_columns = [
    "date",
    "venue",
    "client",
    "amount",
    "logistics",
    "vat",
]

class ExcelHandler:
    def __init__(self, file_path):
        self.file_path = file_path

    def process_invoice(self, data_dict, provided_sheet_name="Apr 26"):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Excel file not found at {self.file_path}")

        sheet_name = data_dict.get("batch", provided_sheet_name)

        # 1. Load Data for Reasoning
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=0)

        except Exception as e:
            if "worksheet named" in str(e).lower():
                self._create_new_sheet(sheet)
                df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=0)

            else:
                return "ERROR", f"Could not read sheet {sheet_name}: {e}"

        # Map Excel Columns to Indexes
        original_cols = [str(c).strip() for c in df.columns.tolist()]
        norm_cols = [c.lower() for c in original_cols]
        
        try:
            indices = {
                "date": norm_cols.index("date"),
                "venue": norm_cols.index("venue"),
                "client": norm_cols.index("client name"),
                "amount": norm_cols.index("amount"),
                "logistic": norm_cols.index("logistic/service charge"),
                "vat": norm_cols.index("vat charged"),
                "rep": norm_cols.index("rep"),
                "remark": norm_cols.index("remark"),
                "extra": norm_cols.index("remark") + 1,
            }
        except ValueError as e:
            return "NOT_FOUND", f"Column mapping error: {e}"

        target_name = str(data_dict.get("client_name", "")).lower()
        target_date_str = str(data_dict.get("date", ""))
        extracted_amount = data_dict.get("amount_payable", 0.0)

        # 2. Attempt to Match Existing Entry
        best_match_idx = -1
        best_score = -1

        for idx, row in df.iterrows():
            row_client = str(row.iloc[indices["client"]]).lower()
            if not row_client or row_client == "nan": continue
            
            score = fuzz.token_sort_ratio(target_name, row_client)
            if score > best_score:
                best_score = score
                best_match_idx = idx

        # Logic: If match is strong (>70), we update. Otherwise, we insert.
        wb = load_workbook(self.file_path)
        sheet = wb[sheet_name]

        # OPTION A: STRONG MATCH FOUND (Potential Update)
        if best_score >= 70:
            matched_row = df.iloc[best_match_idx]
            excel_row = best_match_idx + 2
            
            try:
                existing_amount = float(matched_row.iloc[indices["amount"]]) if not pd.isna(matched_row.iloc[indices["amount"]]) else 0.0
            except:
                existing_amount = 0.0

            # --- DISCREPANCY CHECK ---
            if abs(existing_amount - extracted_amount) > 1.0 and existing_amount > 0:
                log_info(f"₦ mismatch: Invoice {extracted_amount} vs Ledger {existing_amount} for {matched_row.iloc[indices['client']]}", "discrepancies")
                return "DISCREPANCY", f"₦ mismatch: Invoice {extracted_amount} vs Ledger {existing_amount} for {matched_row.iloc[indices['client']]}"

            # Proceed to Update if amount is fine or ledger was 0
            self._write_to_sheet(sheet, excel_row, indices, data_dict, is_update=True)
            wb.save(self.file_path)
            return "MATCHED", f"Updated row {excel_row} for {target_name}"

        else:
            # --- INSERTION LOGIC ---
            insert_row = self._find_insertion_point(df, target_date_str, indices["date"])
            sheet.insert_rows(insert_row)
            
            self._write_to_sheet(sheet, insert_row, indices, data_dict, is_update=False)
            self._copy_style(sheet, insert_row - 1, insert_row) # Keep it looking like the video
            
            wb.save(self.file_path)

            for col in required_columns:
                if data_dict.get(col) == '':
                    return "DISCREPANCY", f"Required column '{col}' not found in Excel file"

            return "CREATED", f"New entry inserted at row {insert_row} for {target_name}"
        
    def _create_new_sheet(self, sheet):
        wb = load_workbook(self.file_path)
        if sheet in wb.sheetnames:
            return 

        wb.create_sheet(sheet)
        sheet = wb[sheet]
        sheet.append(required_columns)
        wb.save(self.file_path)

    def _write_to_sheet(self, sheet, row, idx_map, data, is_update=False):
        """Helper to map data_dict to excel columns"""
        # Static Fields
        sheet.cell(row=row, column=idx_map["date"] + 1).value = data.get("date")
        sheet.cell(row=row, column=idx_map["venue"] + 1).value = data.get("venue")
        sheet.cell(row=row, column=idx_map["client"] + 1).value = data.get("client_name") + ( "/" + data.get("event") if data.get("event") else "")
        sheet.cell(row=row, column=idx_map["amount"] + 1).value = data.get("amount_payable")
        sheet.cell(row=row, column=idx_map["logistic"] + 1).value = data.get("logistics")
        sheet.cell(row=row, column=idx_map["vat"] + 1).value = data.get("vat")
        sheet.cell(row=row, column=idx_map["rep"] + 1).value = data.get("rep", "rep")
        sheet.cell(row=row, column=idx_map["extra"] + 1).value = data.get("extra")
        
        # Smart Remark Handling
        remark_cell = sheet.cell(row=row, column=idx_map["remark"] + 1)
        new_remark = data.get("remark", "")
        same_remark = new_remark == remark_cell.value

        if is_update and remark_cell.value and not same_remark:
            remark_cell.value = f"{remark_cell.value} | {new_remark}"
        else:
            remark_cell.value = new_remark

    def _find_insertion_point(self, df, target_date_str, date_col_idx):
        """Finds the last row of the matching date or the sorted chronological position"""
        last_matching_row = 2 # Default to top (after header)
        
        for idx, row in df.iterrows():
            current_row_date = str(row.iloc[date_col_idx])
            # If we find the same date, keep tracking it to find the *end* of the group
            if target_date_str in current_row_date:
                last_matching_row = idx + 3 # +1 for 0-base, +1 for header, +1 to insert *after*
            # If we hit a row that is 'greater' than our date, we stop and insert here
            # (Simple string comparison works for many date formats, or convert to datetime)
            elif current_row_date > target_date_str and last_matching_row == 2:
                return idx + 2
                
        return last_matching_row

    def _copy_style(self, sheet, src_row, dest_row):
        """Copies cell styles from source row to destination row"""
        for col in range(1, sheet.max_column + 1):
            source_cell = sheet.cell(row=src_row, column=col)
            dest_cell = sheet.cell(row=dest_row, column=col)
            if source_cell.has_style:
                dest_cell.font = source_cell.font.copy()
                dest_cell.border = source_cell.border.copy()
                dest_cell.fill = source_cell.fill.copy()
                dest_cell.alignment = source_cell.alignment.copy()