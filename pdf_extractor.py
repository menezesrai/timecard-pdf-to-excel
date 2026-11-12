import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber


logger = logging.getLogger(__name__)


class PDFExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf = None

    def open_pdf(self):
        self.pdf = pdfplumber.open(self.pdf_path)

    def close_pdf(self):
        if self.pdf:
            self.pdf.close()

    def __enter__(self):
        self.open_pdf()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_pdf()

    def extract_page_data(self, page_num: int) -> Optional[Dict[str, Any]]:
        try:
            page = self.pdf.pages[page_num]

            collaborator = self._extract_collaborator_info(page)
            if not collaborator:
                logger.warning("Dados do colaborador não encontrados na página %s", page_num + 1)
                return None

            work_data = self._extract_work_data(page)
            if not work_data:
                logger.warning("Totais não encontrados na página %s", page_num + 1)
                return None

            return {
                "page_num": page_num + 1,
                "collaborator": collaborator,
                "work_data": work_data,
            }
        except Exception as exc:
            logger.error("Erro ao ler página %s: %s", page_num + 1, exc)
            return None

    def _extract_collaborator_info(self, page) -> Optional[Dict[str, str]]:
        text = page.extract_text() or ""
        if not text:
            return None

        lines = text.splitlines()
        try:
            department, role = self._extract_department_and_function(lines)
            return {
                "nome": self._value_after_label(lines, "NOME"),
                "funcao": role,
                "departamento": department,
                "cpf": self._first_match(r"\d{3}\.\d{3}\.\d{3}-\d{2}", text),
                "admissao": self._extract_admission_date(lines),
            }
        except Exception as exc:
            logger.error("Erro ao ler dados do colaborador: %s", exc)
            return None

    def _extract_admission_date(self, lines: List[str]) -> Optional[str]:
        index = self._find_line_index(lines, "ADMISS")
        if index is None or index + 1 >= len(lines):
            return None

        return self._first_match(r"\d{2}/\d{2}/\d{4}", lines[index + 1])

    def _find_line_index(self, lines: List[str], label: str) -> Optional[int]:
        label = self._normalize_label(label)
        for index, line in enumerate(lines):
            if label in self._normalize_label(line):
                return index
        return None

    def _value_after_label(self, lines: List[str], label: str) -> Optional[str]:
        index = self._find_line_index(lines, label)
        if index is None:
            return None

        line = lines[index]
        match = re.search(rf"{re.escape(label)}:\s*(.+)$", line, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()

        for next_line in lines[index + 1:]:
            cleaned = next_line.strip()
            if cleaned:
                return cleaned

        return None

    def _extract_department_and_function(self, lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
        index = self._find_line_index(lines, "DEPARTAMENTO")
        if index is None:
            return None, None

        value_line = next((line.strip() for line in lines[index + 1:] if line.strip()), "")
        if not value_line:
            return None, None

        match = re.match(r"\S+\s+\S+\s+(.+)$", value_line)
        text = match.group(1).strip() if match else value_line
        normalized_text = self._normalize_label(text)

        for role in sorted(self._known_roles(), key=len, reverse=True):
            if normalized_text.endswith(role):
                department = text[:-len(role)].strip(" -")
                return department or None, text[-len(role):].strip()

        parts = text.rsplit(" ", 3)
        if len(parts) >= 2:
            return parts[0].strip(" -"), " ".join(parts[1:]).strip()

        return text, None

    def _extract_work_data(self, page) -> Optional[Dict[str, Any]]:
        try:
            tables = page.extract_tables()
            if not tables:
                return self._extract_work_data_from_text(page)

            table = max(tables, key=len)
            header_index = self._find_header_row(table)
            if header_index is None:
                return self._extract_work_data_from_text(page)

            columns = self._get_column_indices(table[header_index])
            if not columns:
                return self._extract_work_data_from_text(page)

            data_row = self._extract_data_row(table, header_index, columns)
            if not data_row:
                return self._extract_work_data_from_text(page)

            return {"columns": columns, "data_row": data_row}
        except Exception as exc:
            logger.error("Erro ao extrair totais: %s", exc)
            return None

    def _extract_work_data_from_text(self, page) -> Optional[Dict[str, Any]]:
        text = page.extract_text() or ""
        if not text:
            return None

        header_line = None
        totals_line = None
        for line in text.splitlines():
            if line.startswith("DATA ") and "NORMAIS" in line:
                header_line = line
            elif line.startswith("TOTAIS "):
                totals_line = line

        if not header_line or not totals_line:
            return None

        summary_columns = ["NORMAIS", "EX100%", "EXTRA", "BCRED.", "BDEB.", "NOT TOTAL"]
        present_columns = [column for column in summary_columns if column in header_line]
        values = re.findall(r"\d{1,3}:\d{2}", totals_line)

        if len(values) != len(present_columns):
            logger.warning(
                "Linha TOTAIS tem %s valores para %s colunas",
                len(values),
                len(present_columns),
            )
            return None

        totals = dict(zip(present_columns, values))
        punches = self._extract_punches_from_text(text)

        return {
            "columns": {
                "DATA": 0,
                "EX100%": 1,
                "EXTRA": 2,
                "BCRED.": 3,
                "BDEB.": 4,
                "NOT TOTAL": 5,
            },
            "data_row": {
                "DATA": self._extract_reference_date(text),
                "EX100%": totals.get("EX100%", "00:00"),
                "EXTRA": totals.get("EXTRA", "00:00"),
                "BCRED.": totals.get("BCRED.", "00:00"),
                "BDEB.": totals.get("BDEB.", "00:00"),
                "NOT TOTAL": totals.get("NOT TOTAL", "00:00"),
                "OBS": self._extract_obs_from_text(text),
                "ENTRADA 1": punches.get("ENTRADA 1", ""),
                "SAIDA 1": punches.get("SAIDA 1", ""),
                "ENTRADA 2": punches.get("ENTRADA 2", ""),
                "SAIDA 2": punches.get("SAIDA 2", ""),
            },
        }

    def _extract_punches_from_text(self, text: str) -> Dict[str, str]:
        for line in text.splitlines():
            if not re.match(r"^\d{2}/\d{2}/\d{4}\s+-\s+\S+", line):
                continue

            tokens = line.split()
            values = tokens[3:7] if len(tokens) >= 7 else []
            return {
                "ENTRADA 1": values[0] if len(values) > 0 else "",
                "SAIDA 1": values[1] if len(values) > 1 else "",
                "ENTRADA 2": values[2] if len(values) > 2 else "",
                "SAIDA 2": values[3] if len(values) > 3 else "",
            }

        return {"ENTRADA 1": "", "SAIDA 1": "", "ENTRADA 2": "", "SAIDA 2": ""}

    def _extract_obs_from_text(self, text: str) -> str:
        observations = []
        for line in text.splitlines():
            if not re.match(r"^\d{2}/\d{2}/\d{4}\s+-\s+\S+", line):
                continue

            tokens = line.split()
            entry_values = [tokens[3]] if len(tokens) > 3 else []
            if len(tokens) > 5:
                entry_values.append(tokens[5])

            for value in entry_values:
                if value.strip() and not self._is_time_value(value):
                    observations.append(value.strip())

        return " / ".join(dict.fromkeys(observations))

    def _extract_reference_date(self, text: str) -> str:
        period_match = re.search(r"Per(?:í|i)odo:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if period_match:
            return period_match.group(1)

        row_match = re.search(r"^(\d{2}/\d{2}/\d{4})\s+-\s+\S+", text, re.MULTILINE)
        return row_match.group(1) if row_match else ""

    def _find_header_row(self, table: List[List[str]]) -> Optional[int]:
        for index, row in enumerate(table):
            row_text = " ".join(str(cell) or "" for cell in row).upper()
            if "DATA" in row_text and "ENTRADA" in row_text:
                return index
        return None

    def _get_column_indices(self, header: List[str]) -> Dict[str, int]:
        columns = {}
        for column_name in ["DATA", "EX100%", "EXTRA", "BCRED.", "BDEB.", "NOT TOTAL"]:
            for index, cell in enumerate(header):
                if cell and column_name.upper() in str(cell).upper():
                    columns[column_name] = index
                    break

        return columns if len(columns) >= 6 else {}

    def _extract_data_row(
        self,
        table: List[List[str]],
        header_index: int,
        columns: Dict[str, int],
    ) -> Optional[Dict[str, str]]:
        for row in table[header_index + 1:]:
            row_text = " ".join(str(cell) or "" for cell in row).strip()
            if not row_text.upper().startswith("TOTAIS"):
                continue

            return {
                column_name: str(row[column_index]).strip() if column_index < len(row) and row[column_index] else ""
                for column_name, column_index in columns.items()
            }

        return None

    def extract_all_pages(self) -> List[Dict[str, Any]]:
        total_pages = len(self.pdf.pages)
        extracted_pages = []

        logger.info("Lendo %s páginas", total_pages)
        for page_num in range(total_pages):
            page_data = self.extract_page_data(page_num)
            if page_data:
                extracted_pages.append(page_data)

            if (page_num + 1) % 10 == 0:
                logger.info("%s/%s páginas processadas", page_num + 1, total_pages)

        logger.info("Dados extraídos de %s páginas", len(extracted_pages))
        return extracted_pages

    @staticmethod
    def _first_match(pattern: str, text: str) -> Optional[str]:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    @staticmethod
    def _is_time_value(value: str) -> bool:
        return bool(re.fullmatch(r"\d{1,3}:\d{2}", value.strip()))

    @staticmethod
    def _normalize_label(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(char for char in normalized if not unicodedata.combining(char)).upper()

    @staticmethod
    def _known_roles() -> List[str]:
        return [
            "ENCARREGADO(A) DE LOJA",
            "OPERADOR(A) DE LOJA",
            "OPERADOR(A) DE CAIXA",
            "ASSISTENTE ADMINISTRATIVO",
            "AUXILIAR ADMINISTRATIVO",
            "OFICIAL DE MANUTENCAO",
            "AUXILIAR DE LIMPEZA",
            "SUPERVISOR(A) GERAL",
            "OPERADOR DE CAIXA",
            "ATENDENTE DE LOJA",
            "AUXILIAR DE ESTOQUE",
            "GERENTE DE LOJA I",
            "GERENTE DE LOJA",
            "FISCAL DE LOJA",
            "CONFERENTE",
            "REPOSITOR",
            "GERENTE",
            "CAIXA",
        ]
