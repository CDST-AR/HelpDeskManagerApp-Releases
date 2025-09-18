#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lee uno o varios archivos (cualquier extensión), detecta cuáles son SQLite,
extrae IPv4 de counters.ip (o similares), deduplica por /24 (primeros 3 octetos)
y guarda los rangos A.B.C.1-A.B.C.254 en UNA sola línea separada por comas.

Ahora pregunta dónde guardar el archivo de salida (GUI y fallback por consola).
"""

import sys
import os
import glob
import sqlite3
from contextlib import closing
from typing import Iterable, List, Set, Optional, Tuple
import ipaddress

DEFAULT_OUTPUT_FILENAME = "direcciones de ip.txt"
CANDIDATE_IP_COLUMNS = {"ip", "ip_address", "direccion_ip", "ip_addr"}


def select_files_gui() -> List[str]:
    """Permite elegir múltiples archivos de cualquier tipo (sin filtrar por extensión)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        paths = filedialog.askopenfilenames(
            title="Selecciona uno o más archivos (SQLite)",
            filetypes=[
                ("Todos los archivos", "*"),
                ("SQLite probables", ("*.db3", "*.db", "*.sqlite", "*.sqlite3", "*.db3.*", "*.sqlite.*", "*.sqlite3.*", "*.db.*")),
            ]
        )
        return list(paths)
    except Exception:
        return []


def ask_paths_stdin() -> List[str]:
    """Permite ingresar rutas o patrones (wildcards). Soporta ; , o espacio como separadores."""
    print("Ingresá rutas o patrones (wildcards) separados por ';' o ',' y presioná Enter:")
    print("Ej:  C:\\carpeta\\PrinterMonitorClient.db3.*; D:\\otra\\*.sqlite")
    raw = input("> ").strip()
    sep = ';' if ';' in raw else (',' if ',' in raw else ' ')
    tokens = [p.strip().strip('"') for p in raw.split(sep) if p.strip()]
    # Expandir comodines (glob)
    expanded: List[str] = []
    for t in tokens:
        matches = glob.glob(t)
        expanded.extend(matches if matches else [t])
    return expanded


def is_file(p: str) -> bool:
    try:
        return os.path.isfile(p)
    except Exception:
        return False


def looks_like_sqlite_by_header(path: str) -> bool:
    """Chequea la cabecera 'SQLite format 3\\x00'."""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
        return header == b"SQLite format 3\x00"
    except Exception:
        return False


def is_sqlite_file(path: str) -> bool:
    """
    Verifica si es una DB SQLite: primero por cabecera, y si falla,
    intenta abrir en modo lectura y correr un PRAGMA simple.
    """
    if looks_like_sqlite_by_header(path):
        return True
    # Fallback: intentar abrir
    uri = f"file:{os.path.abspath(path)}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=2) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("PRAGMA schema_version")
                _ = cur.fetchone()
        return True
    except Exception:
        return False


def find_ip_column(conn: sqlite3.Connection) -> Optional[str]:
    try:
        with closing(conn.cursor()) as cur:
            cur.execute("PRAGMA table_info(counters)")
            cols = [row[1] for row in cur.fetchall()]
            if not cols:
                return None
            lower_map = {c.lower(): c for c in cols}
            for cand in CANDIDATE_IP_COLUMNS | {"ip"}:
                if cand in lower_map:
                    return lower_map[cand]
            for c in cols:
                if "ip" in c.lower():
                    return c
    except sqlite3.Error:
        pass
    return None


def extract_ips_from_db(db_path: str) -> Iterable[str]:
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            ip_col = find_ip_column(conn)
            if not ip_col:
                print(f"[AVISO] No se encontró columna 'ip' (o similar) en 'counters' en: {db_path}")
                return []
            with closing(conn.cursor()) as cur:
                cur.execute(f'SELECT "{ip_col}" FROM counters')
                for (val,) in cur.fetchall():
                    if val is not None:
                        yield str(val).strip()
    except sqlite3.OperationalError as e:
        print(f"[ERROR] No se pudo abrir o consultar {db_path}: {e}")
    except sqlite3.Error as e:
        print(f"[ERROR] SQLite en {db_path}: {e}")
    return []


def parse_ipv4(s: str) -> Optional[ipaddress.IPv4Address]:
    # Acepta valores con “ruido” mínimo (ej. "192.168.1.10 puerto 80" -> toma 192.168.1.10)
    cand = s.split()[0]
    try:
        ip = ipaddress.ip_address(cand)
        return ip if isinstance(ip, ipaddress.IPv4Address) else None
    except Exception:
        return None


# ---------------------- Selección de ruta de guardado ----------------------

def ask_save_path_gui(default_filename: str) -> str:
    """Diálogo para elegir dónde guardar el resultado."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.asksaveasfilename(
            title="Guardar resultado como…",
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Archivo de texto", "*.txt"), ("Todos los archivos", "*.*")],
        )
        return path or ""
    except Exception:
        return ""


def ask_save_path_stdin(default_filename: str) -> str:
    """Fallback por consola para elegir la ruta de guardado."""
    print(f"Ruta de guardado (dejar vacío para usar ./{default_filename}):")
    raw = input("> ").strip().strip('"')
    if not raw:
        return os.path.join(os.getcwd(), default_filename)
    # Si el usuario dio solo un nombre, guardamos en el cwd
    if os.path.basename(raw) == raw:
        return os.path.join(os.getcwd(), raw)
    # Crear carpeta si no existe
    try:
        os.makedirs(os.path.dirname(raw), exist_ok=True)
    except Exception:
        pass
    return raw


def get_save_path(default_filename: str = DEFAULT_OUTPUT_FILENAME) -> str:
    path = ask_save_path_gui(default_filename)
    if not path:
        path = ask_save_path_stdin(default_filename)
    return path or os.path.join(os.getcwd(), default_filename)


# ---------------------- NUEVO: función reutilizable para la UI ----------------------

def generate_ip_ranges(paths: Optional[List[str]] = None,
                       save_path: Optional[str] = None) -> Tuple[str, int]:
    """
    Ejecuta el flujo de extracción.
    - paths: lista de rutas a archivos (si None, usa GUI/stdin como en main)
    - save_path: ruta de guardado (si None, pregunta como en main)
    Devuelve (out_path, cantidad_de_rangos).
    Lanza ValueError/IOError en lugar de sys.exit.
    """
    # 1) Rutas: args -> GUI -> stdin
    if paths is None:
        paths = [p for p in sys.argv[1:] if p.strip()]
        if not paths:
            paths = select_files_gui()
        if not paths:
            paths = ask_paths_stdin()

    files = [p for p in paths if is_file(p)]
    if not files:
        raise ValueError("No se proporcionaron rutas de archivos válidas.")

    sqlite_files = [p for p in files if is_sqlite_file(p)]
    if not sqlite_files:
        raise ValueError("Ninguno de los archivos dados es una base SQLite válida.")

    # 2) Extraer solo IPv4 y agrupar por /24
    prefixes_24: Set[str] = set()
    for p in sqlite_files:
        for raw in extract_ips_from_db(p):
            ip4 = parse_ipv4(raw)
            if ip4 is None:
                continue
            a, b, c, _ = str(ip4).split(".")
            prefixes_24.add(f"{a}.{b}.{c}")

    if not prefixes_24:
        one_line = ""
        count = 0
    else:
        ordered_prefixes = sorted(
            prefixes_24,
            key=lambda pfx: ipaddress.IPv4Address(pfx + ".0")
        )
        ranges = [f"{p}.1-{p}.254" for p in ordered_prefixes]
        one_line = ",".join(ranges)  # una sola línea, sin espacios
        count = len(ranges)

    # 3) Guardar
    out_path = save_path or get_save_path(DEFAULT_OUTPUT_FILENAME)
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(one_line)  # no agregamos newline extra

    return out_path, count


# ---------------------- Modo script (consola) ----------------------

def main():
    try:
        out_path, count = generate_ip_ranges()
        if count:
            print(f"[OK] Se guardaron {count} rango(s) /24 en: {out_path}")
        else:
            print(f"[OK] Archivo vacío generado: {out_path}")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
