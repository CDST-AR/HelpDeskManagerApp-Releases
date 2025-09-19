# updater.py
import json
import urllib.request
import os
import sys
import tempfile
import subprocess
import threading
import hashlib
from datetime import datetime, timedelta
from tkinter import Toplevel, StringVar
from tkinter import ttk
from packaging import version

# ===== Config =====
LATEST_URL = "https://raw.githubusercontent.com/CDST-AR/HelpDeskManagerApp-Releases/main/latest.json"

# Paleta igual que la app
ORANGE = "#FF7F00"
BLUE   = "#1E90FF"
BG     = "#FFFFFF"
TEXT   = "#333333"

# --- helpers de UI (agregar junto a _ui_call) ---
def _on_ui_thread() -> bool:
    return threading.current_thread() is threading.main_thread()

def _ui_sync(parent, fn):
    """Ejecuta fn en el hilo de UI; si ya estamos en UI, la ejecuta directo."""
    if _on_ui_thread():
        return fn()
    return _ui_call(parent, fn)

# ===== Tema / estilos =====
def _install_theme(root):
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

def _ui_call(parent, fn):
    done = threading.Event()
    box = {}
    def _wrap():
        try:
            box["value"] = fn()
        finally:
            done.set()
    parent.after(0, _wrap)
    done.wait()
    return box.get("value")

def _ask_yes_no(parent, title, message):
    def _mk():
        top = Toplevel(parent); top.title(title); top.resizable(False, False)
        top.transient(parent); top.grab_set(); _install_theme(top)
        frm = ttk.Labelframe(top, text=title, style="Card.TLabelframe")
        frm.pack(padx=12, pady=12, fill="both")
        ttk.Label(frm, text=message, wraplength=380).pack(padx=10, pady=(10, 6))
        btns = ttk.Frame(frm); btns.pack(pady=(6, 10))
        result = {"ok": False}
        ttk.Button(btns, text="Sí",  style="Big.TButton",
                   command=lambda: (result.update(ok=True), top.destroy())).pack(side="left", padx=6)
        ttk.Button(btns, text="No",  style="Big.TButton",
                   command=top.destroy).pack(side="left", padx=6)
        top.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()-top.winfo_width())//2
        y = parent.winfo_rooty() + (parent.winfo_height()-top.winfo_height())//2
        top.geometry(f"+{max(x,0)}+{max(y,0)}")
        top.wait_window()
        return result["ok"]
    return _ui_sync(parent, _mk)

def _info(parent, title, message):
    def _mk():
        top = Toplevel(parent); top.title(title); top.resizable(False, False)
        top.transient(parent); top.grab_set(); _install_theme(top)
        frm = ttk.Labelframe(top, text=title, style="Card.TLabelframe")
        frm.pack(padx=12, pady=12, fill="both")
        ttk.Label(frm, text=message, wraplength=380).pack(padx=10, pady=(10, 6))
        ttk.Button(frm, text="Aceptar", style="Big.TButton", command=top.destroy).pack(pady=(6, 10))
        top.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()-top.winfo_width())//2
        y = parent.winfo_rooty() + (parent.winfo_height()-top.winfo_height())//2
        top.geometry(f"+{max(x,0)}+{max(y,0)}")
        top.wait_window()
    # 👇 clave: usar _ui_sync, no _ui_call
    _ui_sync(parent, _mk)


def _error(parent, title, message):
    _info(parent, title, message)

# ===== utilidades =====
def _is_newer(remote: str, local: str) -> bool:
    try:
        return version.parse(str(remote)) > version.parse(str(local))
    except Exception:
        return str(remote).strip() != str(local).strip()

def _sha256sum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _this_app_path() -> str:
    return sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])

def _app_dir() -> str:
    return os.path.dirname(_this_app_path())

def _runner_path() -> str:
    """
    Ruta al ejecutable del runner. Cambiá el nombre si lo buildéas distinto.
    """
    # Ej: HelpDeskUpdater.exe (nombre sugerido abajo en el .spec)
    return os.path.join(_app_dir(), "HelpDeskUpdater.exe")

def _marker_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    d = os.path.join(base, os.path.splitext(os.path.basename(_this_app_path()))[0])
    os.makedirs(d, exist_ok=True)
    return d

def _marker_path() -> str:
    return os.path.join(_marker_dir(), "update_marker.json")

def _write_marker(new_version: str):
    data = {"version": new_version, "ts": datetime.utcnow().isoformat()}
    with open(_marker_path(), "w", encoding="utf-8") as f:
        json.dump(data, f)

def _read_marker():
    p = _marker_path()
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _clear_marker():
    try:
        os.remove(_marker_path())
    except Exception:
        pass

def _show_progress(parent, title="Descargando actualización"):
    def _mk():
        top = Toplevel(parent); top.title(title); top.resizable(False, False)
        top.transient(parent); top.grab_set(); _install_theme(top)
        frm = ttk.Labelframe(top, text=title, style="Card.TLabelframe"); frm.pack(padx=12, pady=12, fill="both")
        lbl = ttk.Label(frm, text="Iniciando descarga…"); lbl.pack(padx=16, pady=(8, 6))
        var = StringVar(value="0 %")
        pbar = ttk.Progressbar(frm, length=300, mode="indeterminate"); pbar.pack(padx=16, pady=6)
        pct  = ttk.Label(frm, textvariable=var); pct.pack(padx=16, pady=(0, 8))
        top.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()-top.winfo_width())//2
        y = parent.winfo_rooty() + (parent.winfo_height()-top.winfo_height())//2
        top.geometry(f"+{max(x,0)}+{max(y,0)}")
        return top, pbar, var, lbl
    return _ui_sync(parent, _mk)

def _progress_update(parent, widgets, total, downloaded, have_len):
    def _u():
        top, pbar, var, lbl = widgets
        if have_len and total > 0:
            pct = int(downloaded * 100 / total)
            pbar.configure(mode="determinate", maximum=100, value=pct)
            var.set(f"{pct} %")
            lbl.configure(text=f"Descargando… {downloaded//1024} / {total//1024} KB")
        else:
            if pbar["mode"] != "indeterminate":
                pbar.configure(mode="indeterminate"); pbar.start(10)
            var.set("")
            lbl.configure(text=f"Descargando… {downloaded//1024} KB")
    parent.after(0, _u)

def _close_progress(parent, widgets):
    def _c():
        top, *_ = widgets
        if top and top.winfo_exists():
            top.destroy()
    parent.after(0, _c)

def _download_with_progress(url: str, dest_path: str, on_progress):
    req = urllib.request.Request(url, headers={"User-Agent": "HelpDeskManagerApp-Updater"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest_path, "wb") as out:
        total = r.getheader("Content-Length")
        total = int(total) if total and total.isdigit() else None
        downloaded = 0
        chunk = 1024 * 256
        while True:
            data = r.read(chunk)
            if not data:
                break
            out.write(data)
            downloaded += len(data)
            on_progress(total or 0, downloaded, total is not None)

# ===== API =====
def check_for_updates(parent, app_version: str, latest_url: str = LATEST_URL, auto: bool = False):
    """
    Descarga y verifica el instalador, escribe un marcador para mostrar un mensaje post-update,
    lanza el runner externo con UI, y cierra esta instancia para permitir la actualización.
    """
    def worker():
        widgets = None
        try:
            # 1) latest.json
            req = urllib.request.Request(latest_url, headers={"User-Agent": "HelpDeskManagerApp-Updater"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))

            remote_ver = str(data.get("version", "")).strip()
            url        = str(data.get("url", "")).strip()
            expected   = str(data.get("sha256", "")).lower().strip()
            notes      = str(data.get("notes", "")).strip()

            if not remote_ver or not url:
                if not auto: _error(parent, "Actualizaciones", "No se pudo leer la información de actualización.")
                return

            if not _is_newer(remote_ver, str(app_version)):
                if not auto: _info(parent, "Actualizaciones", f"Ya tenés la última versión ({app_version}).")
                return

            msg = (f"Hay una nueva versión {remote_ver}.\n\n{notes or ''}\n\n"
                   "Se descargará la actualización y la aplicación se cerrará.\n"
                   "Cuando termine, se volverá a abrir automáticamente.")
            if not _ask_yes_no(parent, "Actualización disponible", msg):
                return

            # 2) Descargar con progreso
            fd, tmp_path = tempfile.mkstemp(suffix=".exe"); os.close(fd)
            widgets = _show_progress(parent)
            try:
                _download_with_progress(
                    url, tmp_path,
                    on_progress=lambda t, d, h: _progress_update(parent, widgets, t, d, h)
                )
            except Exception:
                _close_progress(parent, widgets); widgets = None
                os.unlink(tmp_path)
                raise

            # 3) Verificar hash
            if expected:
                got = _sha256sum(tmp_path).lower()
                if got != expected:
                    _close_progress(parent, widgets); widgets = None
                    os.unlink(tmp_path)
                    _error(parent, "Actualizaciones", "Error de verificación: el hash SHA-256 no coincide.")
                    return

            _close_progress(parent, widgets); widgets = None

            # 4) Escribir marcador para el aviso al reiniciar
            _write_marker(remote_ver)

            # 5) Lanzar el runner externo con UI propia
            runner = _runner_path()
            if not os.path.isfile(runner):
                # Fallback: si por algún motivo no está el runner, avisamos y no cerramos sin feedback
                _error(parent, "Actualizaciones", "No se encontró el componente de actualización (HelpDeskUpdater.exe).")
                return

            try:
                subprocess.Popen(
                    [runner, "--installer", tmp_path, "--app", _this_app_path(), "--version", remote_ver, "--delete"],
                    close_fds=True
                )
            except Exception as e:
                _error(parent, "Actualizaciones", f"No se pudo iniciar el actualizador externo:\n{e}")
                return

            # 6) Cerrar esta instancia para permitir la actualización
            parent.after(300, lambda: os._exit(0))

        except Exception as e:
            if widgets:
                _close_progress(parent, widgets)
            if not auto:
                _error(parent, "Actualizaciones", f"No se pudo completar la actualización:\n{e}")

    threading.Thread(target=worker, daemon=True).start()

def auto_check(parent, app_version: str, latest_url: str = LATEST_URL):
    check_for_updates(parent, app_version=app_version, latest_url=latest_url, auto=True)

def show_post_update_if_any(parent):
    data = _read_marker()
    if not data:
        return
    try:
        ts = datetime.fromisoformat(data.get("ts", ""))
    except Exception:
        ts = None

    def _show():
        try:
            if ts and datetime.utcnow() - ts <= timedelta(minutes=30):
                ver = data.get("version", "")
                _info(parent, "Actualizaciones", f"Actualización a {ver} completada correctamente.")
        finally:
            _clear_marker()

    # Ejecutar cuando el loop ya está activo
    parent.after(0, _show)

