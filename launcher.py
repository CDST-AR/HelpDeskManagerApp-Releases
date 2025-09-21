import os, sys, json, hashlib, zipfile, shutil, tempfile, subprocess, traceback
import tkinter as tk
from tkinter import ttk, messagebox

# ===== Config rápida =====
REMOTE_ROOT = r"C:\tmp\releases"  # << CAMBIAR: carpeta compartida
LATEST_JSON = "latest.json"                           # dentro del share
LOCAL_ROOT  = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()),
                           "HelpDeskManagerApp")
APP_DIR_PREFIX = "app-"                               # p.ej., app-1.1.4

# Paleta mínima para el popup
BG, FG = "#FFFFFF", "#333333"

# ===== Util =====
def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def atomic_write_json(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)

def read_json(path: str):
    if not os.path.isfile(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def current_pointer_path() -> str:
    return os.path.join(LOCAL_ROOT, "current.json")

def read_current():
    return read_json(current_pointer_path()) or {}

def write_current(data: dict):
    atomic_write_json(current_pointer_path(), data)

def app_dir(ver: str) -> str:
    return os.path.join(LOCAL_ROOT, f"{APP_DIR_PREFIX}{ver}")

def copy_from_share(src: str, dst: str):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)

def extract_zip(zip_path: str, dest_dir: str):
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir, ignore_errors=True)
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(dest_dir)

def cleanup_old_versions(keep=2):
    if not os.path.isdir(LOCAL_ROOT): return
    dirs = [d for d in os.listdir(LOCAL_ROOT)
            if d.startswith(APP_DIR_PREFIX) and os.path.isdir(os.path.join(LOCAL_ROOT, d))]
    # ordenar por nombre (asumimos vX.Y.Z lexicográfico razonable)
    for d in sorted(dirs, reverse=True)[keep:]:
        shutil.rmtree(os.path.join(LOCAL_ROOT, d), ignore_errors=True)

# ===== UI mínima =====
class Popup:
    def __init__(self, title="HelpDesk Manager", text="Iniciando…"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("420x140")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        s = ttk.Style(self.root); 
        try: s.theme_use("clam")
        except Exception: pass
        ttk.Label(self.root, text=text, background=BG, foreground=FG).pack(pady=(20,10))
        self.lbl = ttk.Label(self.root, text="")
        self.lbl.pack()
        self.pbar = ttk.Progressbar(self.root, mode="indeterminate", length=360)
        self.pbar.pack(pady=8)
        self.pbar.start(10)
        self.root.update_idletasks()

    def set(self, text):
        self.lbl.config(text=text)
        self.root.update_idletasks()

    def done(self):
        try:
            self.pbar.stop()
            self.root.destroy()
        except Exception:
            pass

# ===== Núcleo =====
def ensure_latest_and_get_exe(pop: Popup) -> str:
    # 1) leer latest.json desde el share
    latest_path = os.path.join(REMOTE_ROOT, LATEST_JSON)
    if not os.path.isfile(latest_path):
        raise RuntimeError(f"No encuentro {latest_path}")

    with open(latest_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # latest.json esperado:
    # {
    #   "version": "1.1.4",
    #   "filename": "HelpDeskManagerApp-1.1.4.zip",
    #   "sha256": "<hash del zip>",
    #   "main_exe": "HelpDeskManagerApp.exe"
    # }
    ver = str(meta["version"]).strip()
    zip_name = str(meta["filename"]).strip()
    expected = str(meta.get("sha256", "")).lower().strip()
    main_exe = str(meta.get("main_exe", "HelpDeskManagerApp.exe")).strip()

    cur = read_current()
    cur_ver = cur.get("version", "")
    cur_path = cur.get("path", "")
    cur_exe  = cur.get("exe", main_exe)

    if cur_ver == ver and os.path.isfile(os.path.join(cur_path, cur_exe)):
        # ya estoy al día
        return os.path.join(cur_path, cur_exe)

    # 2) copiar zip a staging
    pop.set(f"Descargando actualización {ver}…")
    src_zip = os.path.join(REMOTE_ROOT, zip_name)
    if not os.path.isfile(src_zip):
        raise RuntimeError(f"No encuentro {src_zip} en el share")

    staging_dir = os.path.join(LOCAL_ROOT, "staging")
    os.makedirs(staging_dir, exist_ok=True)
    dst_zip = os.path.join(staging_dir, zip_name)
    copy_from_share(src_zip, dst_zip)

    # 3) verificar hash
    if expected:
        got = sha256(dst_zip)
        if got != expected:
            raise RuntimeError("Fallo verificación SHA-256 del paquete")

    # 4) descomprimir en app-<ver>
    pop.set("Aplicando actualización…")
    dest = app_dir(ver)
    extract_zip(dst_zip, dest)

    # 5) localizar exe
    exe_path = os.path.join(dest, main_exe)
    if not os.path.isfile(exe_path):
        # tolerar zip con carpeta raíz (dist/...)
        # buscar el exe dentro
        found = None
        for root, _, files in os.walk(dest):
            if main_exe in files:
                found = os.path.join(root, main_exe)
                break
        if not found:
            raise RuntimeError(f"No se encontró {main_exe} dentro del paquete")
        exe_path = found

    # 6) actualizar puntero actual de forma atómica
    write_current({"version": ver, "path": os.path.dirname(exe_path), "exe": os.path.basename(exe_path)})

    # 7) limpiar staging y versiones viejas
    try: shutil.rmtree(staging_dir, ignore_errors=True)
    except Exception: pass
    cleanup_old_versions(keep=2)

    pop.set(f"Actualización {ver} aplicada.")
    return exe_path

def launch(exe_path: str):
    cwd = os.path.dirname(exe_path)
    subprocess.Popen([exe_path], cwd=cwd, close_fds=True)

def main():
    os.makedirs(LOCAL_ROOT, exist_ok=True)
    pop = Popup("HelpDesk Manager", "Comprobando actualizaciones…")
    try:
        exe = ensure_latest_and_get_exe(pop)
        pop.set("Iniciando aplicación…")
        pop.done()
        launch(exe)
    except Exception as e:
        pop.done()
        # Si hay una versión previa usable, lanzar para no dejar al usuario tirado
        cur = read_current()
        fallback = os.path.join(cur.get("path", ""), cur.get("exe", "HelpDeskManagerApp.exe"))
        if os.path.isfile(fallback):
            messagebox.showwarning("HelpDesk Manager",
                                   f"No se pudo actualizar: {e}\n\nSe iniciará la versión actual.")
            launch(fallback)
        else:
            messagebox.showerror("HelpDesk Manager",
                                 f"No se pudo iniciar la app.\n\nDetalle:\n{e}\n\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
