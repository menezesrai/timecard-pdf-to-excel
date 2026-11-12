import ctypes
import re
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path

import pdfplumber

from main import convert_pdf_to_excel


OFN_FILEMUSTEXIST = 0x00001000
OFN_PATHMUSTEXIST = 0x00000800
OFN_EXPLORER = 0x00080000
MB_ICONINFORMATION = 0x00000040
MB_ICONERROR = 0x00000010
MB_OK = 0x00000000
MB_YESNO = 0x00000004
MB_YESNOCANCEL = 0x00000003
IDYES = 6
IDNO = 7
IDCANCEL = 2
SW_SHOWNORMAL = 1
WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_EX_TOPMOST = 0x00000008
WS_EX_DLGMODALFRAME = 0x00000001
PBS_MARQUEE = 0x00000008
PBM_SETMARQUEE = 0x0400 + 10
PM_REMOVE = 0x0001


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ("lStructSize", wintypes.DWORD),
        ("hwndOwner", wintypes.HWND),
        ("hInstance", wintypes.HINSTANCE),
        ("lpstrFilter", wintypes.LPCWSTR),
        ("lpstrCustomFilter", wintypes.LPWSTR),
        ("nMaxCustFilter", wintypes.DWORD),
        ("nFilterIndex", wintypes.DWORD),
        ("lpstrFile", wintypes.LPWSTR),
        ("nMaxFile", wintypes.DWORD),
        ("lpstrFileTitle", wintypes.LPWSTR),
        ("nMaxFileTitle", wintypes.DWORD),
        ("lpstrInitialDir", wintypes.LPCWSTR),
        ("lpstrTitle", wintypes.LPCWSTR),
        ("Flags", wintypes.DWORD),
        ("nFileOffset", wintypes.WORD),
        ("nFileExtension", wintypes.WORD),
        ("lpstrDefExt", wintypes.LPCWSTR),
        ("lCustData", wintypes.LPARAM),
        ("lpfnHook", wintypes.LPVOID),
        ("lpTemplateName", wintypes.LPCWSTR),
        ("pvReserved", wintypes.LPVOID),
        ("dwReserved", wintypes.DWORD),
        ("FlagsEx", wintypes.DWORD),
    ]


def message_box(text, title="Conversor Cartão Ponto", flags=MB_OK):
    return ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def choose_pdf():
    buffer = ctypes.create_unicode_buffer(4096)
    filters = "Arquivos PDF (*.pdf)\0*.pdf\0Todos os arquivos (*.*)\0*.*\0\0"

    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.lpstrFilter = filters
    ofn.lpstrFile = ctypes.cast(buffer, wintypes.LPWSTR)
    ofn.nMaxFile = len(buffer)
    ofn.lpstrTitle = "Escolha o PDF do cartão ponto"
    ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST
    ofn.lpstrDefExt = "pdf"

    if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return buffer.value
    return None


def choose_mode():
    response = message_box(
        "Escolha o tipo de resumo:\n\n"
        "SIM = COMPLETO\n"
        "NÃO = SIMPLES\n\n"
        "COMPLETO: usa todas as regras atuais.\n"
        "SIMPLES: inclui apenas quem tem BancoPOSITIVO diferente de zero.",
        "Tipo de resumo",
        MB_YESNOCANCEL | MB_ICONINFORMATION,
    )
    if response == IDYES:
        return "complete"
    if response == IDNO:
        return "simple"
    return None


def build_output_path(pdf_path, mode="complete"):
    pdf = Path(pdf_path)
    relevant_date = extract_relevant_date(pdf_path)
    suffix = "Completo" if mode == "complete" else "Simples"
    base_name = f"Resumo Cartão de Ponto {suffix} {relevant_date}"
    safe_name = sanitize_filename(base_name)
    return str(unique_path(pdf.parent / f"{safe_name}.xlsx"))


def extract_relevant_date(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return "Data não encontrada"

    period_match = re.search(r"Per(?:í|i)odo:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if period_match:
        return period_match.group(1).replace("/", "-")

    row_match = re.search(r"^(\d{2}/\d{2}/\d{4})\s+-\s+\S+", text, re.MULTILINE)
    if row_match:
        return row_match.group(1).replace("/", "-")

    return "Data não encontrada"


def sanitize_filename(value):
    return re.sub(r'[<>:"/\\|?*]', "-", value).strip(" .")


def unique_path(path):
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def open_folder(folder):
    ctypes.windll.shell32.ShellExecuteW(None, "open", str(folder), None, None, SW_SHOWNORMAL)


def convert_with_progress(pdf_path, output_path, mode):
    result = {"summary": None, "error": None}

    hwnd, progress = create_progress_window()

    def worker():
        try:
            result["summary"] = convert_pdf_to_excel(pdf_path, output_path, mode)
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    msg = MSG()
    while thread.is_alive():
        while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.03)

    thread.join()
    if progress:
        ctypes.windll.user32.SendMessageW(progress, PBM_SETMARQUEE, False, 0)
    if hwnd:
        ctypes.windll.user32.DestroyWindow(hwnd)

    if result["error"]:
        raise result["error"]
    return result["summary"]


def create_progress_window():
    user32 = ctypes.windll.user32
    comctl32 = ctypes.windll.comctl32
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        wintypes.HMENU,
        wintypes.HINSTANCE,
        wintypes.LPVOID,
    ]
    user32.SendMessageW.restype = wintypes.LPARAM
    comctl32.InitCommonControls()

    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    width = 420
    height = 145
    left = int((screen_width - width) / 2)
    top = int((screen_height - height) / 2)

    hwnd = user32.CreateWindowExW(
        WS_EX_TOPMOST | WS_EX_DLGMODALFRAME,
        "STATIC",
        "Gerando Excel",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_VISIBLE,
        left,
        top,
        width,
        height,
        None,
        None,
        None,
        None,
    )
    if not hwnd:
        return None, None

    user32.CreateWindowExW(
        0,
        "STATIC",
        "Gerando o Excel. Por favor, aguarde...",
        WS_CHILD | WS_VISIBLE,
        24,
        24,
        360,
        24,
        hwnd,
        None,
        None,
        None,
    )
    progress = user32.CreateWindowExW(
        0,
        "msctls_progress32",
        "",
        WS_CHILD | WS_VISIBLE | PBS_MARQUEE,
        24,
        62,
        360,
        22,
        hwnd,
        None,
        None,
        None,
    )
    if progress:
        user32.SendMessageW(progress, PBM_SETMARQUEE, True, 30)

    user32.UpdateWindow(hwnd)
    return hwnd, progress


def main():
    if len(sys.argv) in {4, 5} and sys.argv[1] == "--convert":
        mode = sys.argv[4] if len(sys.argv) == 5 else "complete"
        convert_pdf_to_excel(sys.argv[2], sys.argv[3], mode)
        return

    mode = choose_mode()
    if not mode:
        return

    message_box(
        "Na próxima janela, escolha o PDF do cartão ponto.\n\n"
        "Depois disso, aguarde a mensagem de conclusão.",
        flags=MB_ICONINFORMATION,
    )

    pdf_path = choose_pdf()
    if not pdf_path:
        return

    output_path = build_output_path(pdf_path, mode)

    try:
        summary = convert_with_progress(pdf_path, output_path, mode)
    except Exception as exc:
        message_box(
            "Não foi possível converter este PDF.\n\n"
            f"Erro:\n{exc}\n\n"
            "Se o Excel estiver aberto, feche o arquivo e tente novamente.",
            "Erro na conversão",
            MB_OK | MB_ICONERROR,
        )
        return

    response = message_box(
        "Excel criado com sucesso!\n\n"
        f"Registros: {summary['total_records']}\n"
        f"Departamentos: {summary['total_departments']}\n\n"
        f"Arquivo:\n{summary['output_excel']}\n\n"
        "Deseja abrir a pasta agora?",
        "Conversão concluída",
        MB_YESNO | MB_ICONINFORMATION,
    )
    if response == IDYES:
        open_folder(Path(output_path).parent)


if __name__ == "__main__":
    main()

