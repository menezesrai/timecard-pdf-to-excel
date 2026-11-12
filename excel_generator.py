import logging
import re
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config import COMPLETE_EXCEL_HEADERS, SIMPLE_EXCEL_HEADERS


logger = logging.getLogger(__name__)


class ExcelGenerator:
    HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    DATE_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    WHITE_BOLD = Font(bold=True, color="FFFFFF")

    @staticmethod
    def create_workbook(grouped_data: Dict[str, List[Dict[str, Any]]], output_path: str, mode: str = "complete"):
        workbook = Workbook()
        workbook.remove(workbook.active)

        for department, records in sorted(grouped_data.items()):
            ExcelGenerator._create_department_sheet(workbook, department, records, mode)

        workbook.save(output_path)
        logger.info("Planilha salva em %s", output_path)

    @staticmethod
    def _create_department_sheet(workbook: Workbook, department: str, records: List[Dict[str, Any]], mode: str):
        sheet_name = ExcelGenerator._sanitize_sheet_name(department)
        worksheet = workbook.create_sheet(title=sheet_name)
        headers = ExcelGenerator._headers_for_mode(mode)

        ExcelGenerator._write_reference_date(worksheet, records, headers)
        ExcelGenerator._write_headers(worksheet, headers)
        ExcelGenerator._write_data_rows(worksheet, records, mode)
        ExcelGenerator._apply_formatting(worksheet, len(records), mode)

        logger.info("Aba %r criada com %s registros", sheet_name, len(records))

    @staticmethod
    def _headers_for_mode(mode: str) -> List[str]:
        return SIMPLE_EXCEL_HEADERS if mode == "simple" else COMPLETE_EXCEL_HEADERS

    @staticmethod
    def _write_reference_date(worksheet, records: List[Dict[str, Any]], headers: List[str]):
        date_value = records[0].get("data", "") if records else ""
        worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))

        cell = worksheet.cell(row=1, column=1, value=date_value)
        cell.font = ExcelGenerator.WHITE_BOLD
        cell.fill = ExcelGenerator.DATE_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        worksheet.row_dimensions[1].height = 24

    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        sanitized = re.sub(r'[\\/?"*:\[\]]', "", name or "").strip()[:31]
        return sanitized or "Sem Departamento"

    @staticmethod
    def _write_headers(worksheet, headers: List[str]):
        for column, header in enumerate(headers, start=1):
            cell = worksheet.cell(row=2, column=column, value=header)
            cell.font = ExcelGenerator.WHITE_BOLD
            cell.fill = ExcelGenerator.HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    @staticmethod
    def _write_data_rows(worksheet, records: List[Dict[str, Any]], mode: str):
        for row, record in enumerate(records, start=3):
            worksheet.cell(row=row, column=1, value=record.get("nome", ""))
            worksheet.cell(row=row, column=2, value=record.get("funcao", ""))

            if mode == "simple":
                values = [
                    record.get("entrada1", ""),
                    record.get("saida1", ""),
                    record.get("entrada2", ""),
                    record.get("saida2", ""),
                    record.get("bcred", "0"),
                ]
            else:
                values = [
                    record.get("ex100", "0"),
                    record.get("extra", "0"),
                    record.get("bcred", "0"),
                    record.get("bdeb", "0"),
                    record.get("not_total", "0"),
                    record.get("obs", ""),
                ]

            for offset, value in enumerate(values, start=3):
                worksheet.cell(row=row, column=offset, value=value)

    @staticmethod
    def _apply_formatting(worksheet, num_rows: int, mode: str):
        headers = ExcelGenerator._headers_for_mode(mode)
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        highlighted_columns = {7: "008000"} if mode == "simple" else {
            3: "00B0F0",
            5: "008000",
            6: "FF0000",
        }

        for row in worksheet.iter_rows(min_row=2, max_row=num_rows + 2, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(
                    horizontal="center" if cell.column >= 3 else "left",
                    vertical="center",
                )

                if cell.row > 2 and cell.column in highlighted_columns and ExcelGenerator._is_nonzero_value(cell.value):
                    cell.font = Font(bold=True, color=highlighted_columns[cell.column])

        worksheet.row_dimensions[2].height = 30
        ExcelGenerator._adjust_column_widths(worksheet, headers)

    @staticmethod
    def _is_nonzero_value(value) -> bool:
        if value is None:
            return False

        text = str(value).strip()
        if not text:
            return False

        if ":" in text:
            try:
                hours, minutes = text.split(":", 1)
                return int(hours) != 0 or int(minutes) != 0
            except ValueError:
                return False

        try:
            return float(text.replace(",", ".")) != 0
        except ValueError:
            return False

    @staticmethod
    def _adjust_column_widths(worksheet, headers: List[str]):
        for column in range(1, len(headers) + 1):
            max_length = 0
            for cells in worksheet.iter_cols(min_col=column, max_col=column):
                for cell in cells:
                    value = "" if cell.value is None else str(cell.value)
                    max_length = max(max_length, len(value))

            worksheet.column_dimensions[get_column_letter(column)].width = min(max(max_length + 3, 12), 60)
