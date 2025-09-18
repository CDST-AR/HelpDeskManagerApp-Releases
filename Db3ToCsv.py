# db3_to_csv.py
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List

import numpy as np
import pandas as pd

# Modelos especiales que fuerzan CLASE=20 cuando counterclass_id=40
MODELOS_ESPECIALES = {
    "C4010ND", "CLX_6260_Series", "CLX_9201", "HP_PageWide_Color_MFP_E58650", "X4300LX", "CLP_680_Series",
    "FD_E8_48_50_20_50_61_67_65_57_69_64_65_20_50_72_6F_20_34_35_32_64_77_20_50_72_69_6E_74_65_72",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_46_50_20_4D_35_37_37",
    "Samsung_CLP_680_Series", "CLP_670_Series", "P774ADM05",
    "FD_E8_48_50_20_50_61_67_65_57_69_64_65_20_4D_46_50_20_50_35_37_37_35_30",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_36_35_31",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_36_35_32",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_35_30_36",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_36_30_35",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_36_30_38",
    "HP_PageWide_MFP_P57750", "HP_Color_LaserJet_MFP_M577"
}

# -------------------- utilidades base --------------------

def validar_fecha_iso(fecha: str) -> bool:
    """True si fecha tiene formato DD/MM/YYYY."""
    try:
        datetime.strptime(fecha, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def _fecha_param(fecha_maxima_str: str) -> str:
    """Convierte 'DD/MM/YYYY' a 'YYYY-MM-DD 00:00:00' + 1 día (límite exclusivo)."""
    dt = datetime.strptime(fecha_maxima_str, "%d/%m/%Y") + timedelta(days=1)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def conectar_db(filename: str) -> sqlite3.Connection:
    """Devuelve una conexión sqlite3; el caller maneja excepciones."""
    return sqlite3.connect(filename)

def verificar_estructura(conn: sqlite3.Connection) -> bool:
    """Chequea columnas esperadas en tabla 'counters'."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(counters)")
    cols = {row[1] for row in cur.fetchall()}
    requeridas = {"serialnumber", "readdate", "readvalue", "model", "counterclass_id"}
    return requeridas.issubset(cols)

def ejecutar_consulta(conn: sqlite3.Connection, fecha_maxima: Optional[str]) -> pd.DataFrame:
    """
    Lee counters (clases 40/10/20). Si fecha_maxima (DD/MM/YYYY) se provee, aplica readdate < fecha+1d.
    """
    base_query = (
        "SELECT serialnumber, readdate, readvalue, model, counterclass_id "
        "FROM counters WHERE counterclass_id IN (40,10,20)"
    )
    if fecha_maxima:
        if not validar_fecha_iso(fecha_maxima):
            raise ValueError("fecha_maxima debe tener formato DD/MM/YYYY")
        query = base_query + " AND readdate < ?"
        return pd.read_sql(query, conn, params=(_fecha_param(fecha_maxima),))
    return pd.read_sql(base_query, conn)

# -------------------- flujo principal DB3 -> CSV --------------------

def procesar_db3_a_csv(
    archivos_db3: List[str],
    fecha_maxima: Optional[str],
    nombre_base_salida: str,
    carpeta_salida: Optional[str] = None,
) -> str:
    """
    Une lecturas desde múltiples .db3, aplica reglas TIPO/CLASE, reestructura 10/20 y exporta CSV.
    Devuelve la ruta del archivo generado.

    Parámetros:
        archivos_db3: lista de rutas .db3
        fecha_maxima: 'YYYY-MM-DD' o None
        nombre_base_salida: prefijo sin extensión para el archivo final
        carpeta_salida: carpeta destino; por defecto, la del primer .db3
    """
    if not archivos_db3:
        raise ValueError("Se requiere al menos un archivo .db3.")
    if fecha_maxima and not validar_fecha_iso(fecha_maxima):
        raise ValueError("fecha_maxima inválida; use YYYY-MM-DD.")
    if not nombre_base_salida:
        raise ValueError("nombre_base_salida no puede ser vacío.")

    # Leer y unir
    dfs: List[pd.DataFrame] = []
    for path in archivos_db3:
        with conectar_db(path) as conn:
            if not verificar_estructura(conn):
                raise RuntimeError(f"Estructura inesperada en DB: {path}")
            df = ejecutar_consulta(conn, fecha_maxima)
            if df is None or df.empty:
                continue
            dfs.append(df)

    if not dfs:
        raise RuntimeError("No se obtuvieron datos de los .db3 proporcionados.")

    df = pd.concat(dfs, ignore_index=True)

    # ----- Transformaciones -----
    # TIPO: 40 -> 15; otros -> 7
    df.insert(df.columns.get_loc("readvalue"), "TIPO", np.where(df["counterclass_id"].eq(40), 15, 7))

    # CLASE (40 + modelo especial -> 20; 40 -> 10; resto mantiene)
    clase = np.where(
        df["counterclass_id"].eq(40) & df["model"].isin(MODELOS_ESPECIALES),
        "20",
        np.where(df["counterclass_id"].eq(40), "10", df["counterclass_id"].astype(str)),
    )
    df["CLASE"] = clase

    # Renombrar columnas
    df = df.rename(
        columns={
            "serialnumber": "SERIE",
            "readdate": "FECHA",
            "model": "MODELO",
            "readvalue": "CONTADOR",
        }
    )

    # Orden/fecha
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df = df.sort_values("FECHA", ascending=False)
    df["FECHA"] = df["FECHA"].dt.strftime("%d/%m/%Y")

    # Columnas finales y deduplicación
    df = df[["SERIE", "FECHA", "TIPO", "CLASE", "MODELO", "CONTADOR"]]
    df = df.drop_duplicates(subset=["SERIE", "CLASE"], keep="first")
    df = df.sort_values("SERIE")

    # Reestructuración 10/20
    df10 = df[(df["CLASE"] == "10") | ((df["TIPO"] == 15) & (df["CLASE"] == "20"))]
    df20 = df[df["CLASE"] == "20"]
    merged = pd.merge(df10, df20, on=("SERIE", "FECHA", "TIPO"), how="outer", suffixes=("_10", "_20"))

    out = pd.DataFrame(
        {
            "SERIE": merged["SERIE"],
            "FECHA": merged["FECHA"],
            "TIPO": merged["TIPO"].fillna(0).astype(int),
            "CLASE": merged["CLASE_10"].combine_first(merged["CLASE_20"]),
            "CONTADOR": merged["CONTADOR_10"].combine_first(merged["CONTADOR_20"]),
        }
    )
    out["CONTADOR"] = out["CONTADOR"].fillna(0).astype(int)

    # ----- Exportación -----
    base_folder = carpeta_salida or os.path.dirname(archivos_db3[0])
    nombre_archivo = f"{nombre_base_salida}_{os.path.basename(base_folder)}_AutoCSV.csv"
    file_path = os.path.join(base_folder, nombre_archivo)

    out.to_csv(file_path, sep=";", index=False, encoding="utf-8", lineterminator="\n")
    return file_path

