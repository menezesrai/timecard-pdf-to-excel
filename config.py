from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_PDF_PATH = PROJECT_ROOT / "input.pdf"
OUTPUT_EXCEL_PATH = PROJECT_ROOT / "output.xlsx"

COLUMNS_TO_CHECK = ["EX100%", "EXTRA", "BCRED.", "BDEB.", "NOT TOTAL"]

COMPLETE_EXCEL_HEADERS = [
    "Nome",
    "Função",
    "EXTRA FERIADO",
    "EXTRA DOMINGO",
    "BancoPOSITIVO",
    "BancoNEGATIVO",
    "Adc. Noturno",
    "OBS",
]

SIMPLE_EXCEL_HEADERS = [
    "Nome",
    "Função",
    "ENTRADA 1",
    "SAÍDA 1",
    "ENTRADA 2",
    "SAÍDA 2",
    "BancoPOSITIVO",
]

EXCEL_HEADERS = COMPLETE_EXCEL_HEADERS

LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "extraction.log"

TREAT_EMPTY_AS_ZERO = True
