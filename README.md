# Accounting Automation

Accounting Automation extracts invoice data from PDF files and records the
results in an Excel ledger. It is designed for invoice batches that need OCR,
optional AI-assisted field extraction, ledger matching, and basic discrepancy
handling.

> **Current status:** the core processing flow is implemented, but the project
> still requires local setup and a report template before it can process a
> real batch. See [`bin/core/NEXT_STEPS.md`](bin/core/NEXT_STEPS.md) for the
> known gaps and recommended completion work.

## What it currently does

When `main.py` is run, the application:

1. Accepts a folder path from `--folder`, or opens a folder picker when no
   folder is supplied.
2. Finds PDF files directly inside that folder.
3. Converts each PDF page to an image and extracts text with Tesseract OCR.
4. Processes OCR results in batches of up to four files.
5. Uses the OpenRouter API to extract invoice fields as JSON.
6. Reads `data/templates/report.xlsx` and selects the invoice batch worksheet.
7. Matches an invoice to an existing ledger row using fuzzy client-name
   matching.
8. Updates a matching row, inserts a new row, or reports an amount
   discrepancy.
9. Moves successfully processed PDFs to `Processed/` and discrepancy PDFs to
   `Flagged_Discrepancies/`.
10. Writes unresolved and discrepancy information to `data/logs/`.

The extracted data is intended to include the invoice date, venue, client,
amount payable, total cost, logistics/service charge, VAT, discount,
referrer, remarks, and extra discount information. The Excel template's
column names and worksheet layout are part of the current application
contract.

## Requirements

- Python 3.10 or newer
- Tesseract OCR
- Poppler (`pdftoppm`/`pdfinfo`), required by `pdf2image`
- An Excel report template at `data/templates/report.xlsx`
- An OpenRouter API key and model name when using the current AI workflow

On Debian/Ubuntu, the system tools can be installed with:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

On Windows, install Tesseract OCR and Poppler separately. The code contains
support for bundled Windows binaries under `bin/Tesseract-OCR/` and
`bin/poppler/bin/`, but those binaries are not included in this repository.

## Installation

```bash
git clone https://github.com/DavidTimi1/accounting-automation.git
cd accounting-automation

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create the runtime directories and copy the report template into the expected
location:

```bash
mkdir -p data/templates data/logs
# Copy your report workbook to data/templates/report.xlsx
```

The template must contain the worksheet used for the processing period and
columns equivalent to:

- `Date`
- `Venue`
- `Client Name`
- `Amount`
- `Logistic/Service Charge`
- `VAT Charged`
- `Rep`
- `Remark`

The handler uses the worksheet name supplied by the invoice's `batch` value,
or the `--period` value when using the normal extraction path.

## Configuration

Copy `.env.example` to `.env` and set the values:

```dotenv
OMP_THREAD_LIMIT=1
OPENROUTER_API_KEY=your-openrouter-key
AI_MODEL=your-openrouter-model
```

The current entry point always selects the `AI` extraction mode, so both
`OPENROUTER_API_KEY` and `AI_MODEL` are required for the default workflow.
The repository also contains a regex-based `NORMAL` extraction mode, but it is
not currently exposed as a command-line option.

## Running it

Process a selected folder and use the current month as the period:

```bash
python main.py --folder /path/to/invoices
```

Provide a worksheet period explicitly:

```bash
python main.py --period "Apr 26" --folder /path/to/invoices
```

If `--folder` is omitted, a desktop folder picker is opened. Only `.pdf`
files directly in the selected folder are processed; nested directories are
not scanned.

## Output and file handling

During processing, the application creates these directories inside the input
folder:

- `Processed/` — invoices that were matched or inserted successfully
- `Flagged_Discrepancies/` — invoices whose amount differs from the ledger

Operational logs are written under `data/logs/`. The `data/` directory is
ignored by Git because it can contain workbooks, logs, and invoice-related
runtime data.

## Important limitations

- A report workbook is not currently committed; it must be supplied locally.
- OCR quality depends on the invoice scan and the local Tesseract/Poppler
  installation.
- AI extraction depends on the OpenRouter service, selected model, network
  access, and valid JSON being returned.
- The current AI batching logic is intended for ordinary batches and should be
  tested carefully when some files fail OCR.
- Existing ledger matching is based primarily on fuzzy client-name matching;
  it does not provide a durable invoice ID reconciliation strategy.
- The application moves input PDFs after processing, so use a copy of the
  source folder until the workflow has been validated.
- There is no automated test suite or packaged desktop/CLI distribution yet.

## Project layout

```text
.
├── app/core/
│   ├── ai_client.py         # OpenRouter requests and invoice JSON extraction
│   ├── data_extraction.py   # AI and regex-based extraction paths
│   ├── excel_handler.py     # Ledger matching, updates, and inserts
│   ├── ocr_engine.py        # PDF-to-image conversion and Tesseract OCR
│   └── utils.py              # JSON-lines style runtime logging
├── bin/
│   ├── core/NEXT_STEPS.md   # Remaining work and completion checklist
│   ├── poppler_template/    # Placeholder for bundled Poppler assets
│   └── tessaract_template/  # Placeholder for bundled Tesseract assets
├── main.py                  # Command-line entry point
├── requirements.txt
└── .env.example
```

## License

This project is distributed under the license in [`LICENSE`](LICENSE).
