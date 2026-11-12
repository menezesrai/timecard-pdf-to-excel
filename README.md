# Timecard PDF to Excel

I built this application to reduce the time spent reviewing timecard PDFs. A single file could contain many employees, but only part of those pages needed attention. Reading the entire document and reorganising the results by hand made the same task longer every month.

The application reads the PDF, keeps the records with relevant time entries and creates an Excel workbook organised by department. The result is still meant to be reviewed, but the repetitive sorting is already done.

## What it does

- reads multi-page PDFs with `pdfplumber`;
- extracts employee, department and hour totals;
- skips pages without relevant entries;
- creates an `.xlsx` file with one sheet per department;
- offers complete and simplified exports;
- includes a Tkinter desktop interface and a command-line entry point.

## Run locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run it from the command line:

```bash
python main.py caminho\entrada.pdf caminho\saida.xlsx --mode complete
```

Or open the desktop interface:

```bash
python app.py
```

## Export modes

`complete` includes overtime, positive balance, negative balance, night work and notes.

`simple` keeps a shorter view with clock-in, clock-out and positive balance values.

## Project structure

```text
app.py              Tkinter interface
app_exe.py          Windows executable entry point
main.py             Main conversion flow
pdf_extractor.py    PDF reading and extraction
data_processor.py   Record filtering and organisation
excel_generator.py  Workbook writing and formatting
config.py           Headers and simple settings
tests/              Processing rule tests
```

## Privacy

Real input and output files are not part of this repository. The `.gitignore` blocks PDFs, spreadsheets, logs, executables and build folders so employee records are not committed by accident.

## Tests

```bash
python -m unittest discover -s tests
```
