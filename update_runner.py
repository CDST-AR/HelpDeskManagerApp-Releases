# update_runner.py
import argparse
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

# === Paleta (igual que la app) ===
ORANGE = "#FF7F00"
BLUE   = "#1E90FF"
BG     = "#FFFFFF"
TEXT   = "#333333"

def install_theme(root: tk.Misc):
    style = ttk.Style(root)
    root.configure(bg=BG)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=ORANGE, background=BG)
    style.configure("Sub.TLabel", foreground=BLUE, background=BG)
    style.configure("Card.TLabelframe", background=BG, relief="groove", borderwidth=1)
    style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=TEXT, background=BG)
    style.configure("Big.TButton", font=("Segoe UI", 10), padding=(10, 8))

def run_installer(installer_path: str, label: ttk.Label, pbar: ttk.Progressbar, on_done):
    """
    Ejecuta el instalador en modo silencioso y llama on_done(rc) al terminar.
    Mantiene la UI viva con una barra indeterminada.
    """
    def worker():
        args = [installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
        try:
            proc = subprocess.Popen(args)
            rc = proc.wait()
        except Exception as e:
            rc = 999  # error arbitrario para señalar fallo
        finally:
            on_done(rc)
    threading.Thread(target=worker, daemon=True).start()

def main():
    ap = argparse.ArgumentParser(description="Runner de instalación y relanzado de la app.")
    ap.add_argument("--installer", required=True, help="Ruta absoluta al instalador .exe descargado")
    ap.add_argument("--app",       required=True, help="Ruta al ejecutable principal de la app")
    ap.add_argument("--version",   default="",    help="Versión destino (opcional, solo texto UI)")
    ap.add_argument("--delete",    action="store_true", help="Eliminar el instalador al finalizar")
    args = ap.parse_args()

    installer_path = os.path.abspath(args.installer)
    app_path       = os.path.abspath(args.app)
    version_txt    = args.version.strip()

    root = tk.Tk()
    root.title("Actualizando…")
    root.geometry("420x160")
    root.minsize(420, 160)
    # mantener arriba un momento para que el usuario la vea
    root.attributes("-topmost", True)
    root.after(500, lambda: root.attributes("-topmost", False))

    install_theme(root)

    frame = ttk.Labelframe(root, text="Instalación", style="Card.TLabelframe")
    frame.pack(fill="both", expand=True, padx=12, pady=12)

    title = f"Instalando actualización {version_txt}…" if version_txt else "Instalando actualización…"
    ttk.Label(frame, text=title, style="Header.TLabel").pack(anchor="w", padx=8, pady=(6, 2))

    lbl = ttk.Label(frame, text="Por favor, espere… (esto puede tardar unos minutos)")
    lbl.pack(anchor="w", padx=8, pady=(2, 6))

    pbar = ttk.Progressbar(frame, mode="indeterminate", length=360)
    pbar.pack(padx=8, pady=(0, 8))
    pbar.start(10)

    def on_done(rc: int):
        # Actualizar UI al terminar
        def finalize():
            pbar.stop()
            if rc == 0:
                lbl.config(text="Instalación completada. Iniciando la aplicación…")
                # breve pausa para que el usuario vea el texto
                root.update_idletasks()
                root.after(600, lambda: None)
                try:
                    subprocess.Popen([app_path], close_fds=True)
                except Exception:
                    pass
                # (opcional) eliminar el instalador descargado
                if args.delete:
                    try:
                        os.remove(installer_path)
                    except Exception:
                        pass
                # cerrar esta ventana
                root.after(800, root.destroy)
            else:
                lbl.config(text=f"El instalador devolvió código {rc}. Cerrá esta ventana e intenta nuevamente.")
        root.after(0, finalize)

    run_installer(installer_path, lbl, pbar, on_done)
    root.mainloop()

if __name__ == "__main__":
    main()
