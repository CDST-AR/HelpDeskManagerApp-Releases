# updater.py
import json
import urllib.request
import os
import tempfile
import subprocess
import threading
import hashlib
from tkinter import messagebox
from packaging import version  # comparación robusta de versiones

# URL correcta al RAW del latest.json en tu repo
LATEST_URL = "https://raw.githubusercontent.com/CDST-AR/HelpDeskManagerApp-Releases/main/latest.json"

# ---------------- utilidades de versión / hash ---------------- #

def _is_newer(remote: str, local: str) -> bool:
    """
    Devuelve True si remote > local, usando packaging.version.
    Acepta '1.2.3', '1.2.3-post1', etc.
    """
    try:
        return version.parse(str(remote)) > version.parse(str(local))
    except Exception:
        # Fallback muy conservador si algo raro pasa
        return str(remote).strip() != str(local).strip()

def _sha256sum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _launch_installer(path: str):
    """
    Ejecuta el instalador Inno Setup de forma silenciosa.
    Ajustá flags si querés ver UI (usar /SILENT o sin flags).
    """
    args = [path, "/VERYSILENT", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]
    subprocess.Popen(args)

# ---------------- API principal ---------------- #

def check_for_updates(parent, app_version: str, latest_url: str = LATEST_URL, auto: bool = False):
    """
    Busca actualizaciones en background.
    - parent: root/ventana Tk (para los messagebox)
    - app_version: versión local (ej. '1.0.0')
    - latest_url: URL al latest.json (usar RAW)
    - auto: si True, no muestra 'ya estás al día' ni errores benignos
    """
    def worker():
        try:
            req = urllib.request.Request(latest_url, headers={"User-Agent": "HelpDeskManagerApp-Updater"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))

            remote_ver = str(data.get("version", "")).strip()
            url = str(data.get("url", "")).strip()
            expected_sha = str(data.get("sha256", "")).lower().strip()
            notes = str(data.get("notes", "")).strip()

            if not remote_ver or not url:
                if not auto:
                    messagebox.showinfo("Actualizaciones", "No se pudo leer la información de actualización.", parent=parent)
                return

            if not _is_newer(remote_ver, str(app_version)):
                if not auto:
                    messagebox.showinfo("Actualizaciones", f"Ya tenés la última versión ({app_version}).", parent=parent)
                return

            # Confirmar con el usuario
            if not messagebox.askyesno(
                "Actualización disponible",
                f"Hay una nueva versión {remote_ver}.\n\n{notes or ' '}\n¿Descargar e instalar ahora?",
                parent=parent
            ):
                return

            # Descargar a un archivo temporal
            fd, tmp_path = tempfile.mkstemp(suffix=".exe")
            os.close(fd)
            try:
                urllib.request.urlretrieve(url, tmp_path)
            except Exception as e:
                os.unlink(tmp_path)
                raise e

            # Verificación opcional SHA-256
            if expected_sha:
                got = _sha256sum(tmp_path).lower()
                if got != expected_sha:
                    os.unlink(tmp_path)
                    messagebox.showerror("Actualizaciones", "Error de verificación: el hash SHA-256 no coincide.", parent=parent)
                    return

            # Lanzar instalador (silencioso). Podés cerrar la app si querés:
            _launch_installer(tmp_path)
            # parent.after(300, parent.destroy)  # descomentá si querés cerrar la app al iniciar el instalador

        except Exception as e:
            if not auto:
                messagebox.showerror("Actualizaciones", f"No se pudo completar la actualización:\n{e}", parent=parent)

    threading.Thread(target=worker, daemon=True).start()

def auto_check(parent, app_version: str, latest_url: str = LATEST_URL):
    """Chequeo silencioso (no molesta si no hay update)."""
    check_for_updates(parent, app_version=app_version, latest_url=latest_url, auto=True)
