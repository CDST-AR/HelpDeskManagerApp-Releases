import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# ---- Opcional GUI (solo si abrís con doble clic) ----
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
except Exception:  # si no hay tkinter, seguimos solo CLI
    tk = None


CHUNK = 1024 * 1024  # 1 MiB


def sha256_file(path: Path, show_progress=True) -> str:
    """Devuelve el SHA-256 de 'path' leyendo en streaming."""
    total = path.stat().st_size
    h = hashlib.sha256()
    done = 0

    with path.open("rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
            if show_progress and total:
                done += len(b)
                pct = int(done * 100 / total)
                # barra simple en consola
                bar = "#" * (pct // 4)
                sys.stdout.write(f"\r[{bar:<25}] {pct:3d}%")
                sys.stdout.flush()

    if show_progress and total:
        sys.stdout.write("\n")
    return h.hexdigest().lower()


def find_latest_exe(candidates: list[Path]) -> Path | None:
    """Busca el .exe más nuevo dentro de las carpetas candidatas."""
    exes: list[Path] = []
    for base in candidates:
        if not base.exists():
            continue
        for p in base.glob("*.exe"):
            if p.is_file():
                exes.append(p)
    if not exes:
        return None
    exes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return exes[0]


def copy_to_clipboard(text: str):
    """Copia al portapapeles sin dependencias externas."""
    if tk is None:
        return
    r = tk.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(text)
    r.update()  # mantener el portapapeles al cerrar
    r.destroy()


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    print(f"[OK] Escrito: {path}")


def make_latest_json(out_dir: Path, version: str, url: str, sha256: str, notes: str = "Cambios de la versión…"):
    data = {
        "version": version,
        "url": url,
        "sha256": sha256,
        "notes": notes,
    }
    path = out_dir / "latest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Generado: {path}")


def gui_flow(default_dirs: list[Path]):
    """Modo GUI (doble clic): selector de archivo + prompts."""
    if tk is None:
        print("[INFO] Tkinter no disponible; abrí por consola con argumentos.")
        sys.exit(2)

    root = tk.Tk()
    root.withdraw()

    # Intento preselección: .exe más nuevo
    pre = find_latest_exe(default_dirs)
    initialdir = pre.parent.as_posix() if pre else str(default_dirs[0])

    path_str = filedialog.askopenfilename(
        parent=root,
        title="Seleccioná el instalador (.exe)",
        initialdir=initialdir,
        filetypes=[("Instaladores", "*.exe"), ("Todos los archivos", "*.*")],
    )
    if not path_str:
        return

    exe = Path(path_str)
    if not exe.exists():
        messagebox.showerror("Hash instalador", f"No existe el archivo:\n{exe}")
        return

    print(f"Archivo: {exe}")
    sha = sha256_file(exe, show_progress=True)
    print(f"SHA-256: {sha}")
    copy_to_clipboard(sha)

    out_dir = exe.parent
    write_text(out_dir / "sha256.txt", sha)

    if messagebox.askyesno("latest.json", "¿Querés generar latest.json ahora?"):
        ver = simpledialog.askstring("Versión", "Ingresá la versión (ej: v1.0.8):", parent=root) or ""
        url = simpledialog.askstring("URL", "Pegá la URL del instalador:", parent=root) or ""
        notes = simpledialog.askstring("Notas", "Notas (opcional):", parent=root) or "Cambios de la versión…"
        if ver.strip() and url.strip():
            make_latest_json(out_dir, ver.strip(), url.strip(), sha, notes.strip())
            messagebox.showinfo("OK", "latest.json generado.")
        else:
            messagebox.showwarning("Aviso", "Se omitió latest.json (faltó versión o URL).")


def cli_flow():
    """Modo CLI con argparse."""
    parser = argparse.ArgumentParser(
        description="Calcula SHA-256 de un instalador y genera latest.json (opcional)."
    )
    parser.add_argument("--exe", help="Ruta al instalador .exe")
    parser.add_argument("--url", help="URL del asset para latest.json (opcional)")
    parser.add_argument("--version", help="Versión para latest.json, ej: v1.0.8 (opcional)")
    parser.add_argument("--outdir", help="Carpeta donde escribir sha256.txt/latest.json (por defecto: carpeta del .exe)")
    parser.add_argument("--no-progress", action="store_true", help="No mostrar barra de progreso")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()

    # Dirs por defecto donde buscar si no pasás --exe
    defaults = [
        script_dir / "Output",
        cwd / "Output",
        script_dir / "dist",
        cwd / "dist",
        script_dir,
        cwd,
    ]

    if args.exe:
        exe = Path(args.exe).expanduser().resolve()
        if not exe.exists():
            print(f"[ERROR] No existe el archivo: {exe}")
            sys.exit(1)
    else:
        exe = find_latest_exe(defaults)
        if not exe:
            print("[ERROR] No se encontró un .exe. Pasá --exe o dejá el archivo en Output/dist/carpeta actual.")
            sys.exit(1)

    print(f"Archivo: {exe}")
    sha = sha256_file(exe, show_progress=not args.no_progress)
    print(f"SHA-256: {sha}")

    copy_to_clipboard(sha)

    out_dir = Path(args.outdir).resolve() if args.outdir else exe.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    write_text(out_dir / "sha256.txt", sha)

    if args.url and args.version:
        make_latest_json(out_dir, args.version.strip(), args.url.strip(), sha)
    else:
        print("[INFO] latest.json no generado (faltan --version y/o --url).")


if __name__ == "__main__":
    # Si se ejecuta con doble clic (sin parámetros), usamos GUI; si hay parámetros, CLI.
    if len(sys.argv) == 1:
        script_dir = Path(__file__).resolve().parent
        cwd = Path.cwd()
        defaults = [
            script_dir / "Output",
            cwd / "Output",
            script_dir / "dist",
            cwd / "dist",
            script_dir,
            cwd,
        ]
        gui_flow(defaults)
    else:
        cli_flow()
