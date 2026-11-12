import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from main import convert_pdf_to_excel


class CartaoPontoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Cartão Ponto para Excel")
        self.root.geometry("580x390")
        self.root.minsize(540, 360)

        self.pdf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.mode = tk.StringVar(value="complete")
        self.status_text = tk.StringVar(value="Escolha o PDF do cartão ponto para começar.")

        self._build_ui()

    def _build_ui(self):
        self.root.configure(bg="#f4f6f8")

        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Body.TLabel", font=("Segoe UI", 11))
        style.configure("Primary.TButton", font=("Segoe UI", 12, "bold"), padding=10)
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=8)

        ttk.Label(frame, text="Cartão Ponto para Excel", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text="Selecione um PDF, escolha o tipo de resumo e gere a planilha.",
            style="Body.TLabel",
            wraplength=520,
        ).pack(anchor="w", pady=(8, 22))

        file_row = ttk.Frame(frame)
        file_row.pack(fill="x")

        self.file_entry = ttk.Entry(file_row, textvariable=self.pdf_path, font=("Segoe UI", 10))
        self.file_entry.pack(side="left", fill="x", expand=True, ipady=6)

        self.choose_button = ttk.Button(
            file_row,
            text="Escolher PDF",
            command=self.choose_pdf,
            style="Secondary.TButton",
        )
        self.choose_button.pack(side="left", padx=(10, 0))

        mode_row = ttk.Frame(frame)
        mode_row.pack(fill="x", pady=(16, 0))
        ttk.Label(mode_row, text="Resumo", style="Body.TLabel").pack(side="left")

        self.mode_selector = ttk.Combobox(
            mode_row,
            textvariable=self.mode,
            values=("complete", "simple"),
            state="readonly",
            width=14,
        )
        self.mode_selector.pack(side="left", padx=(10, 0))

        self.convert_button = ttk.Button(
            frame,
            text="Converter para Excel",
            command=self.start_conversion,
            style="Primary.TButton",
        )
        self.convert_button.pack(fill="x", pady=(22, 14))

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x")

        ttk.Label(
            frame,
            textvariable=self.status_text,
            style="Body.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(16, 10))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(6, 0))

        self.open_folder_button = ttk.Button(
            actions,
            text="Abrir pasta do Excel",
            command=self.open_output_folder,
            state="disabled",
            style="Secondary.TButton",
        )
        self.open_folder_button.pack(side="left")

    def choose_pdf(self):
        path = filedialog.askopenfilename(
            title="Escolha o PDF do cartão ponto",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.pdf_path.set(path)
            self.output_path.set("")
            self.open_folder_button.configure(state="disabled")
            self.status_text.set("PDF escolhido. Clique em converter para gerar o Excel.")

    def start_conversion(self):
        pdf_path = self.pdf_path.get().strip()
        if not pdf_path:
            messagebox.showwarning("PDF não escolhido", "Escolha um arquivo PDF antes de converter.")
            return

        if not Path(pdf_path).exists():
            messagebox.showerror("Arquivo não encontrado", "Não consegui encontrar o PDF escolhido.")
            return

        output_path = self._build_output_path(pdf_path)
        self.output_path.set(output_path)
        self._set_busy(True)

        threading.Thread(
            target=self._convert_in_background,
            args=(pdf_path, output_path, self.mode.get()),
            daemon=True,
        ).start()

    def _convert_in_background(self, pdf_path: str, output_path: str, mode: str):
        try:
            summary = convert_pdf_to_excel(pdf_path, output_path, mode)
            self.root.after(0, self._show_success, summary)
        except Exception as exc:
            self.root.after(0, self._show_error, str(exc))

    def _show_success(self, summary):
        self._set_busy(False)
        self.open_folder_button.configure(state="normal")
        self.status_text.set(
            "Pronto! Excel criado com "
            f"{summary['total_records']} registros em {summary['total_departments']} departamentos."
        )
        messagebox.showinfo(
            "Conversão concluída",
            "O Excel foi criado com sucesso.\n\n"
            f"Arquivo:\n{summary['output_excel']}",
        )

    def _show_error(self, message: str):
        self._set_busy(False)
        self.status_text.set("Não foi possível converter este PDF. Veja o extraction.log para detalhes.")
        messagebox.showerror("Erro na conversão", message)

    def _set_busy(self, busy: bool):
        if busy:
            self.status_text.set("Convertendo... aguarde alguns instantes.")
            self.progress.start(12)
            self.choose_button.configure(state="disabled")
            self.convert_button.configure(state="disabled")
            self.mode_selector.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            return

        self.progress.stop()
        self.choose_button.configure(state="normal")
        self.convert_button.configure(state="normal")
        self.mode_selector.configure(state="readonly")

    def _build_output_path(self, pdf_path: str) -> str:
        pdf = Path(pdf_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(pdf.parent / f"{pdf.stem}_convertido_{timestamp}.xlsx")

    def open_output_folder(self):
        output_path = self.output_path.get().strip()
        folder = Path(output_path).parent if output_path else Path.cwd()
        os.startfile(folder)


def main():
    root = tk.Tk()
    CartaoPontoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
