import argparse
import logging
import sys
from pathlib import Path

from config import INPUT_PDF_PATH, LOG_FILE, OUTPUT_EXCEL_PATH
from data_processor import DataProcessor
from excel_generator import ExcelGenerator
from pdf_extractor import PDFExtractor


logger = logging.getLogger(__name__)


def configure_logging():
    if logging.getLogger().handlers:
        return

    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if sys.stdout:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def convert_pdf_to_excel(input_pdf_path, output_excel_path=OUTPUT_EXCEL_PATH, mode="complete"):
    mode = mode.lower().strip()
    if mode not in {"complete", "simple"}:
        raise ValueError("Modo inválido. Use 'complete' ou 'simple'.")

    configure_logging()

    input_pdf_path = Path(input_pdf_path)
    output_excel_path = Path(output_excel_path)

    if not input_pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {input_pdf_path}")

    logger.info("Iniciando conversão em modo %s", mode)

    with PDFExtractor(str(input_pdf_path)) as extractor:
        pages = extractor.extract_all_pages()

    if not pages:
        raise RuntimeError("Nenhum dado foi extraído do PDF. Verifique o layout do arquivo.")

    records = DataProcessor.process_all_pages(pages, mode)
    if not records:
        raise RuntimeError("Nenhum registro passou pelos filtros configurados.")

    grouped_records = DataProcessor.group_by_department(records)
    DataProcessor.validate_data_consistency(grouped_records)
    ExcelGenerator.create_workbook(grouped_records, str(output_excel_path), mode)

    summary = {
        "input_pdf": str(input_pdf_path),
        "output_excel": str(output_excel_path),
        "total_departments": len(grouped_records),
        "total_records": len(records),
        "mode": mode,
        "departments": {
            department: len(items)
            for department, items in sorted(grouped_records.items())
        },
    }

    logger.info(
        "Conversão concluída: %s registros em %s departamentos",
        summary["total_records"],
        summary["total_departments"],
    )
    return summary


def build_parser():
    parser = argparse.ArgumentParser(
        description="Converte PDFs de cartão ponto em planilhas Excel."
    )
    parser.add_argument("input_pdf", nargs="?", default=INPUT_PDF_PATH)
    parser.add_argument("output_excel", nargs="?", default=OUTPUT_EXCEL_PATH)
    parser.add_argument("--mode", choices=("complete", "simple"), default="complete")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    try:
        convert_pdf_to_excel(args.input_pdf, args.output_excel, args.mode)
        return 0
    except Exception as exc:
        configure_logging()
        logger.error("Falha na conversão: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
