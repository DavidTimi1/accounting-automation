# Project next steps

This file records the work still needed before Accounting Automation should be
treated as a complete, repeatable production tool.

## Required before a first real run

- [ ] Add or provision a validated `data/templates/report.xlsx` workbook.
- [ ] Confirm the workbook worksheet names match the invoice batch format
      (for example, `Apr 26`).
- [ ] Install and verify Tesseract OCR and Poppler on each target machine.
- [ ] Configure `OPENROUTER_API_KEY` and `AI_MODEL` in `.env`.
- [ ] Run the application against copied sample invoices, not the source
      folder, and inspect both the workbook and moved files.
- [ ] Review the generated files under `data/logs/` after a sample run.

## Functional completion

- [ ] Add a CLI option to choose `AI` or `NORMAL` extraction instead of always
      selecting `AI` in `main.py`.
- [ ] Fix and test the missing-worksheet path in `ExcelHandler`; the current
      code calls `_create_new_sheet` with an undefined variable.
- [ ] Define and validate one stable invoice schema shared by AI extraction,
      regex extraction, and Excel writing.
- [ ] Make AI response-to-file mapping robust when OCR errors or failed
      batches occur.
- [ ] Validate required fields before writing or moving an invoice.
- [ ] Add a dry-run mode so users can inspect proposed ledger changes without
      moving source files.
- [ ] Add explicit handling for duplicate invoices and a stable invoice
      identifier.
- [ ] Make processing resumable and safe if the application stops midway.

## Reliability and maintainability

- [ ] Add unit tests for invoice parsing, numeric cleanup, date extraction,
      fuzzy matching, discrepancy thresholds, and insertion ordering.
- [ ] Add an integration test using a small fixture workbook and sample OCR
      text.
- [ ] Replace broad exception handling with specific errors and actionable
      messages.
- [ ] Ensure `data/logs/` exists before logging so logging cannot mask the
      original processing error.
- [ ] Add structured logging and a summary containing counts for processed,
      flagged, unresolved, and skipped files.
- [ ] Pin and periodically review dependency versions for the supported Python
      versions.

## Distribution

- [ ] Decide whether Tesseract and Poppler should be installed by the user or
      bundled for supported platforms.
- [ ] If bundling, populate the `bin/` templates and verify the PyInstaller
      resource paths on Windows and Linux.
- [ ] Add a documented release process and a sample configuration.
- [ ] Provide a small, sanitized fixture project so new contributors can run
      the workflow without access to private invoices.
