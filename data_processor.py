import logging
import re
from typing import Any, Dict, List, Optional

from config import COLUMNS_TO_CHECK, TREAT_EMPTY_AS_ZERO


logger = logging.getLogger(__name__)


class DataProcessor:
    @staticmethod
    def convert_to_numeric(value: str):
        if not value:
            return 0.0 if TREAT_EMPTY_AS_ZERO else None

        try:
            cleaned = str(value).strip().replace(" ", "")
            time_match = re.fullmatch(r"(\d{1,3}):(\d{2})", cleaned)
            if time_match:
                hours, minutes = time_match.groups()
                return int(hours) * 60 + int(minutes)

            return float(cleaned.replace(",", "."))
        except ValueError:
            logger.warning("Valor não numérico ignorado: %r", value)
            return 0.0 if TREAT_EMPTY_AS_ZERO else None

    @staticmethod
    def should_include_page(work_data: Dict[str, Any], mode: str = "complete") -> bool:
        data_row = work_data.get("data_row", {})

        if mode == "simple":
            value = DataProcessor.convert_to_numeric(data_row.get("BCRED.", "0"))
            return value is not None and value != 0

        if data_row.get("OBS"):
            return True

        for column_name in COLUMNS_TO_CHECK:
            value = DataProcessor.convert_to_numeric(data_row.get(column_name, "0"))
            if value is not None and value != 0:
                return True

        return False

    @staticmethod
    def process_page(page_data: Dict[str, Any], mode: str = "complete") -> Optional[Dict[str, Any]]:
        try:
            if not DataProcessor.should_include_page(page_data["work_data"], mode):
                return None

            collaborator = page_data["collaborator"]
            work_data = page_data["work_data"]["data_row"]

            return {
                "nome": collaborator.get("nome", "N/A"),
                "funcao": collaborator.get("funcao", "N/A"),
                "departamento": collaborator.get("departamento", "N/A"),
                "data": work_data.get("DATA", ""),
                "ex100": work_data.get("EX100%", "0"),
                "extra": work_data.get("EXTRA", "0"),
                "bcred": work_data.get("BCRED.", "0"),
                "bdeb": work_data.get("BDEB.", "0"),
                "not_total": work_data.get("NOT TOTAL", "0"),
                "obs": work_data.get("OBS", ""),
                "entrada1": work_data.get("ENTRADA 1", ""),
                "saida1": work_data.get("SAIDA 1", ""),
                "entrada2": work_data.get("ENTRADA 2", ""),
                "saida2": work_data.get("SAIDA 2", ""),
                "page_num": page_data["page_num"],
            }
        except Exception as exc:
            logger.error(
                "Erro ao processar página %s: %s",
                page_data.get("page_num", "desconhecida"),
                exc,
            )
            return None

    @staticmethod
    def process_all_pages(all_page_data: List[Dict[str, Any]], mode: str = "complete") -> List[Dict[str, Any]]:
        records = []
        skipped = 0

        for page_data in all_page_data:
            record = DataProcessor.process_page(page_data, mode)
            if record:
                records.append(record)
            else:
                skipped += 1

        logger.info("%s registros aproveitados; %s páginas ignoradas", len(records), skipped)
        return records

    @staticmethod
    def group_by_department(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped = {}

        for record in records:
            department = record.get("departamento") or "SEM DEPARTAMENTO"
            grouped.setdefault(department, []).append(record)

        for department_records in grouped.values():
            department_records.sort(key=lambda item: item.get("nome", "").upper())

        logger.info("Registros agrupados em %s departamentos", len(grouped))
        return grouped

    @staticmethod
    def validate_data_consistency(grouped_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        issues = []

        for department, records in grouped_data.items():
            if not records:
                issues.append(f"Departamento sem registros: {department}")

            for record in records:
                if not record.get("nome"):
                    issues.append(f"Registro sem nome em {department}")
                if not record.get("funcao"):
                    issues.append(f"Registro sem função: {record.get('nome')}")

        for issue in issues[:5]:
            logger.warning(issue)

        return not issues
