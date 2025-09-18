# falta_contador.py
import os
from datetime import datetime
from typing import Optional

import pandas as pd


def _validar_fecha_dmy(fecha: str) -> None:
    """Valida formato DD/MM/YYYY; lanza ValueError si no cumple."""
    try:
        datetime.strptime(fecha, "%d/%m/%Y")
    except ValueError:
        raise ValueError("fecha_nueva debe tener formato DD/MM/YYYY")


def filtrar_falta_contador_csv(
    archivo_csv_entrada: str,
    fecha_nueva: str,
    nombre_cliente: str,
    carpeta_salida: Optional[str] = None,
    delimiter_entrada: str = ",",
) -> str:
    """
    Filtra filas con Tipo == 'FALTA CONTADOR', normaliza columnas y exporta CSV.
    - fecha_nueva: string DD/MM/YYYY (se escribe en la columna FECHA)
    - nombre_cliente: se usa para armar el nombre del archivo de salida
    - carpeta_salida: si no se indica, usa la carpeta del CSV de entrada
    - delimiter_entrada: separador del CSV de entrada (por defecto coma)

    Devuelve: ruta completa del archivo CSV generado.
    """
    # Validaciones básicas
    if not os.path.isfile(archivo_csv_entrada):
        raise FileNotFoundError(f"No existe el archivo: {archivo_csv_entrada}")
    if not nombre_cliente:
        raise ValueError("nombre_cliente es obligatorio")
    if not fecha_nueva:
        raise ValueError("fecha_nueva es obligatoria")
    _validar_fecha_dmy(fecha_nueva)

    # Leer
    datos = pd.read_csv(archivo_csv_entrada, delimiter=delimiter_entrada)

    # Chequeo de columna clave
    if "Tipo" not in datos.columns:
        raise KeyError("La columna 'Tipo' no existe en el CSV de entrada.")

    # Filtrar solo 'FALTA CONTADOR'
    datos = datos[datos["Tipo"] == "FALTA CONTADOR"].copy()
    if datos.empty:
        raise ValueError("No se encontraron filas con Tipo == 'FALTA CONTADOR'.")

    # Columnas a eliminar si existen
    cols_drop = [
        "Empresa1", "Sucursal1", "Articulo1", "Sector1", "FechaTomaContadorActual",
        "ContActual", "Impresiones_Realizadas", "BackupDe", "CenCosto",
    ]
    datos.drop(columns=[c for c in cols_drop if c in datos.columns], inplace=True, errors="ignore")

    # Renombres si existen esas columnas originales
    rename_map = {
        "Nro_serie": "SERIE",
        "FechaTomaContadorAnterior1": "FECHA",
        "ImpreContadorAnterior": "CONTADOR",
    }
    to_rename = {k: v for k, v in rename_map.items() if k in datos.columns}
    if to_rename:
        datos.rename(columns=to_rename, inplace=True)

    # Asegurar columnas destino y asignar valores
    if "SERIE" not in datos.columns:
        raise KeyError("No se encontró la columna 'SERIE' ni 'Nro_serie' para renombrar.")
    if "CONTADOR" not in datos.columns:
        raise KeyError("No se encontró la columna 'CONTADOR' ni 'ImpreContadorAnterior' para renombrar.")

    datos["FECHA"] = fecha_nueva  # DD/MM/YYYY
    if "TIPO" not in datos.columns:
        datos["TIPO"] = ""
    if "CLASE" not in datos.columns:
        datos["CLASE"] = ""

    # Mapear CLASE desde NombreClase si existe (Color -> 20, resto -> 10)
    if "NombreClase" in datos.columns:
        datos.loc[datos["NombreClase"] == "Color", "CLASE"] = "20"
        datos.loc[datos["NombreClase"] != "Color", "CLASE"] = "10"

    # Forzar TIPO = 14 como en tu lógica original
    datos["TIPO"] = "14"

    # Reordenar columnas principales primero
    principales = ["SERIE", "FECHA", "TIPO", "CLASE", "CONTADOR"]
    resto = [c for c in datos.columns if c not in principales]
    datos = datos[principales + resto]

    # Limpiar columnas ya no necesarias
    for c in ("Tipo", "NombreClase"):
        if c in datos.columns:
            datos.drop(columns=c, inplace=True, errors="ignore")

    # Salida
    carpeta_base = carpeta_salida or os.path.dirname(archivo_csv_entrada)
    nombre_carpeta = os.path.basename(carpeta_base) or os.path.basename(os.path.dirname(archivo_csv_entrada))
    nombre_archivo = f"{nombre_cliente}_{nombre_carpeta}_CSVen0.csv"
    ruta_salida = os.path.join(carpeta_base, nombre_archivo)

    datos.to_csv(ruta_salida, sep=";", index=False, encoding="utf-8", lineterminator="\n")
    return ruta_salida
