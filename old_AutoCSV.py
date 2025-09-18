import os
import sys
import subprocess
import sqlite3
import tkinter as tk
from tkinter import Button, Label, filedialog, messagebox, simpledialog
from datetime import datetime, timedelta
from typing import Optional, List

import pandas as pd
import numpy as np

from Clientes_suma import convertir_xls_a_csv_arcos
import Estimador_manual



MODELOS_ESPECIALES = {
    "C4010ND", "CLX_6260_Series", "CLX_9201", "HP_PageWide_Color_MFP_E58650", "X4300LX", "CLP_680_Series",
    "FD_E8_48_50_20_50_61_67_65_57_69_64_65_20_50_72_6F_20_34_35_32_64_77_20_50_72_69_6E_74_65_72",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_46_50_20_4D_35_37_37", "Samsung_CLP_680_Series",
    "CLP_670_Series", "P774ADM05",
    "FD_E8_48_50_20_50_61_67_65_57_69_64_65_20_4D_46_50_20_50_35_37_37_35_30",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_36_35_31",
    "FD_E8_48_50_20_43_6F_6C_6F_72_20_4C_61_73_65_72_4A_65_74_20_4D_36_35_32",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_35_30_36",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_36_30_35",
    "FD_E8_48_50_20_4C_61_73_65_72_4A_65_74_20_4D_36_30_38",
    "HP_PageWide_MFP_P57750", "HP_Color_LaserJet_MFP_M577"
}


class AutoCSVApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("AutoCSV")
        self.root.geometry("300x500")
        self.root.configure(bg="#ffffff")
        try:
            self.root.iconbitmap("ico.ico")
        except tk.TclError:
            print("El archivo de icono no se encontró.")

        self.fecha_maxima: Optional[str] = None
        self.datos_cargados: Optional[pd.DataFrame] = None

        self._build_ui()

    # -------------------- UTILIDADES --------------------

    def info(self, title: str, msg: str) -> None:
        messagebox.showinfo(title, msg, parent=self.root)

    def warn(self, title: str, msg: str) -> None:
        messagebox.showwarning(title, msg, parent=self.root)

    def error(self, title: str, msg: str) -> None:
        messagebox.showerror(title, msg, parent=self.root)

    def ask_text(self, title: str, prompt: str, initial: str = "") -> Optional[str]:
        return simpledialog.askstring(title, prompt, initialvalue=initial, parent=self.root)

    def conectar_db(self, filename: str) -> Optional[sqlite3.Connection]:
        try:
            return sqlite3.connect(filename)
        except sqlite3.Error as e:
            self.error("Error", f"Error al conectar a la base de datos: {e}")
            return None

    @staticmethod
    def _validar_fecha_iso(fecha: str) -> bool:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def verificar_estructura(conn: sqlite3.Connection) -> bool:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(counters)")
        cols = {row[1] for row in cur.fetchall()}
        requeridas = {"serialnumber", "readdate", "readvalue", "model", "counterclass_id"}
        return requeridas.issubset(cols)

    @staticmethod
    def _fecha_param(fecha_maxima_str: str) -> str:
        """ Convierte 'YYYY-MM-DD' a 'YYYY-MM-DD 00:00:00' + 1 día (límite exclusivo). """
        dt = datetime.strptime(fecha_maxima_str, "%Y-%m-%d") + timedelta(days=1)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # -------------------- SQL --------------------

    def ejecutar_consulta(self, conn: sqlite3.Connection, fecha_maxima: Optional[str]) -> Optional[pd.DataFrame]:
        base_query = (
            "SELECT serialnumber, readdate, readvalue, model, counterclass_id "
            "FROM counters WHERE counterclass_id IN (40,10,20)"
        )
        try:
            if fecha_maxima:
                param = self._fecha_param(fecha_maxima)
                query = base_query + " AND readdate < ?"
                return pd.read_sql(query, conn, params=(param,))
            else:
                return pd.read_sql(base_query, conn)
        except pd.errors.DatabaseError as e:
            self.error("Error", f"Error al ejecutar la consulta SQL: {e}")
            return None

    # -------------------- FLOWS --------------------

    def cargar_y_guardar_archivos(self) -> None:
        archivos = filedialog.askopenfilenames(
            title="Selecciona archivos DB3",
            parent=self.root
        )
        if not archivos:
            return

        if not self.fecha_maxima:
            hoy = datetime.now().strftime("%Y-%m-%d")
            fecha = self.ask_text("Fecha máxima", "Ingrese la fecha máxima:", hoy)
            if not fecha or not self._validar_fecha_iso(fecha):
                self.error("Error", "Fecha máxima no válida (use formato YYYY-MM-DD).")
                self.fecha_maxima = None
                return
            self.fecha_maxima = fecha

        dfs: List[pd.DataFrame] = []
        carpeta_db3 = os.path.dirname(archivos[0])

        errores: List[str] = []
        for path in archivos:
            conn = self.conectar_db(path)
            if not conn:
                errores.append(f"No se pudo conectar: {path}")
                continue
            try:
                if not self.verificar_estructura(conn):
                    errores.append(f"Estructura inesperada en: {path}")
                    continue
                df = self.ejecutar_consulta(conn, self.fecha_maxima)
                if df is None or df.empty:
                    errores.append(f"Sin datos en: {path}")
                    continue
                dfs.append(df)
            finally:
                conn.close()

        if errores:
            # Mostramos un resumen, pero seguimos si obtuvimos algo útil
            self.warn("Avisos", "Algunos archivos tuvieron problemas:\n- " + "\n- ".join(errores))

        if not dfs:
            self.error("Error", "No se obtuvieron datos de los archivos seleccionados.")
            self.datos_cargados = None
            return

        df = pd.concat(dfs, ignore_index=True)

        # ---- TIPO y CLASE (vectorizado) ----
        df.insert(df.columns.get_loc('readvalue'), 'TIPO', np.where(df['counterclass_id'].eq(40), 15, 7))

        clase = df['counterclass_id'].astype(str)
        clase = np.where(
            df['counterclass_id'].eq(40) & df['model'].isin(MODELOS_ESPECIALES),
            '20',
            np.where(df['counterclass_id'].eq(40), '10', clase)
        )
        df['CLASE'] = clase

        # Renombrados
        df = df.rename(columns={
            'serialnumber': 'SERIE',
            'readdate': 'FECHA',
            'model': 'MODELO',
            'readvalue': 'CONTADOR'
        })

        # Orden y formato fecha
        df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
        df = df.sort_values('FECHA', ascending=False)
        df['FECHA'] = df['FECHA'].dt.strftime('%d/%m/%Y')

        # Columnas y dedupe
        df = df[['SERIE', 'FECHA', 'TIPO', 'CLASE', 'MODELO', 'CONTADOR']]
        df = df.drop_duplicates(subset=['SERIE', 'CLASE'], keep='first')
        df = df.sort_values('SERIE')

        # ---- Reestructuración 10/20 (vectorizado sin apply) ----
        df10 = df[(df['CLASE'] == '10') | ((df['TIPO'] == 15) & (df['CLASE'] == '20'))]
        df20 = df[df['CLASE'] == '20']

        merged = pd.merge(
            df10, df20, on=('SERIE', 'FECHA', 'TIPO'), how='outer',
            suffixes=('_10', '_20')
        )

        # Tomamos primero la de clase 10; si falta, la de clase 20
        out = pd.DataFrame({
            'SERIE': merged['SERIE'],
            'FECHA': merged['FECHA'],
            'TIPO': merged['TIPO'].fillna(0).astype(int),
            'CLASE': merged['CLASE_10'].combine_first(merged['CLASE_20']),
            'CONTADOR': merged['CONTADOR_10'].combine_first(merged['CONTADOR_20'])
        })

        out['CONTADOR'] = out['CONTADOR'].fillna(0).astype(int)

        nombre = self.ask_text("Nombre del archivo", "Ingrese el nombre del archivo (sin extensión):")
        if not nombre:
            self.error("Error", "No se ingresó un nombre de archivo válido.")
            self.datos_cargados = None
            self.fecha_maxima = None
            return

        nombre_archivo = f"{nombre}_{os.path.basename(carpeta_db3)}_AutoCSV.csv"
        file_path = os.path.join(carpeta_db3, nombre_archivo)

        try:
            # newline='' evita líneas en blanco extra en Windows
            out.to_csv(file_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            self.info("Éxito", f"Archivo guardado exitosamente en:\n{file_path}")
        except Exception as e:
            self.error("Error", f"No se pudo guardar el archivo CSV: {e}")
        finally:
            self.datos_cargados = None
            self.fecha_maxima = None

    def filtrar_falta_contador(self) -> None:
        archivo_csv = filedialog.askopenfilename(
            title="Selecciona un archivo CSV", filetypes=[("Archivos CSV", "*.csv")], parent=self.root
        )
        if not archivo_csv:
            return

        try:
            fecha_nueva = self.ask_text("Fecha", "Ingrese la fecha que desea poner en la columna FECHA:")
            if not fecha_nueva:
                return

            self.info("Fecha ingresada", "La fecha se ha ingresado correctamente.")

            datos = pd.read_csv(archivo_csv, delimiter=',')
            datos = datos[datos['Tipo'] == 'FALTA CONTADOR'].copy()

            # Drop columnas extra si existen
            cols_drop1 = [
                "Empresa1", "Sucursal1", "Articulo1", "Sector1", "FechaTomaContadorActual",
                "ContActual", "Impresiones_Realizadas", "BackupDe", "CenCosto"
            ]
            datos.drop(columns=[c for c in cols_drop1 if c in datos.columns], inplace=True, errors='ignore')

            # Renombrar si existen
            rename_map = {
                "Nro_serie": "SERIE",
                "FechaTomaContadorAnterior1": "FECHA",
                "ImpreContadorAnterior": "CONTADOR"
            }
            datos.rename(columns={k: v for k, v in rename_map.items() if k in datos.columns}, inplace=True)

            datos['FECHA'] = fecha_nueva

            if 'TIPO' not in datos.columns:
                datos['TIPO'] = ''
            if 'CLASE' not in datos.columns:
                datos['CLASE'] = ''

            if 'NombreClase' in datos.columns:
                datos.loc[datos['NombreClase'] == 'Color', 'CLASE'] = '20'
                datos.loc[datos['NombreClase'] != 'Color', 'CLASE'] = '10'

            datos['TIPO'] = '14'

            # Reordenar columnas principales primero
            principales = ['SERIE', 'FECHA', 'TIPO', 'CLASE', 'CONTADOR']
            resto = [c for c in datos.columns if c not in principales]
            datos = datos[principales + resto]

            # Limpiar columnas ya no necesarias
            datos.drop(columns=[c for c in ('Tipo', 'NombreClase') if c in datos.columns], inplace=True, errors='ignore')

            nombre_cliente = self.ask_text("Nombre del Cliente", "Ingrese el nombre del cliente:")
            if not nombre_cliente:
                self.error("Error", "No se ingresó un nombre de cliente válido.")
                return

            nombre_carpeta = os.path.basename(os.path.dirname(archivo_csv))
            nombre_archivo = f"{nombre_cliente}_{nombre_carpeta}_CSVen0.csv"
            file_path = os.path.join(os.path.dirname(archivo_csv), nombre_archivo)

            datos.to_csv(file_path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            self.info("Éxito", f"Archivo filtrado guardado exitosamente en:\n{file_path}")

        except Exception as e:
            self.error("Error", f"No se pudo procesar el archivo CSV: {e}")

    def ejecutar_extraer_ips(self) -> None:
        """
        Lanza extraer_ips.py en un proceso separado y notifica al terminar.
        """
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extraer_ips.py")
        if not os.path.isfile(script_path):
            self.warn(
                "Script no encontrado",
                f"No se encontró 'extraer_ips.py' en:\n{script_path}\nSeleccioná el archivo manualmente."
            )
            script_path = filedialog.askopenfilename(
                title="Seleccioná extraer_ips.py",
                filetypes=[("Scripts de Python", "*.py"), ("Todos los archivos", "*.*")],
                parent=self.root
            )
            if not script_path:
                return

        try:
            creationflags = 0
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW

            proc = subprocess.Popen([sys.executable, script_path], creationflags=creationflags)

            def notify_when_done():
                ret = proc.poll()
                if ret is None:
                    self.root.after(600, notify_when_done)
                else:
                    if ret == 0:
                        self.info("Extracción de IPs", "Listo. El extractor finalizó.")
                    else:
                        self.warn("Extracción de IPs", f"El extractor terminó con código {ret}. Revisá la consola o el log.")

            self.root.after(600, notify_when_done)

        except Exception as e:
            self.error("Error al ejecutar extraer_ips.py", str(e))

    # -------------------- UI --------------------

    def _build_ui(self) -> None:
        label_titulo = Label(self.root, text="AutoCSV", font=("Helvetica Neue", 16, "bold"),
                             bg="#ffffff", fg="#f4951f")
        label_titulo.pack(pady=10)

        # Procesar archivos DB3
        frame_carga_guardar = tk.Frame(self.root, bg="#ffffff")
        frame_carga_guardar.pack(pady=10)
        tk.Label(frame_carga_guardar, text="Cargar CSV", font=("Helvetica Neue", 9, "bold"),
                 bg="#ffffff", fg="#1669a4").pack()
        Button(frame_carga_guardar, text="Procesar archivos",
               command=self.cargar_y_guardar_archivos, font=("Helvetica Neue", 8)).pack(pady=5)

        # Estimación en 0
        frame_filtro = tk.Frame(self.root, bg="#ffffff")
        frame_filtro.pack(pady=10)
        tk.Label(frame_filtro, text="Estimacion en 0:", font=("Helvetica Neue", 9, "bold"),
                 bg="#ffffff", fg="#1669a4").pack()
        Button(frame_filtro, text="Cargar CSV Contadores por Proceso",
               command=self.filtrar_falta_contador, font=("Helvetica Neue", 8)).pack(pady=5)

        # Estimación con suma fija
        frame_convertir = tk.Frame(self.root, bg="#ffffff")
        frame_convertir.pack(pady=10)
        tk.Label(frame_convertir, text="Estimacion con suma fija:", font=("Helvetica Neue", 9, "bold"),
                 bg="#ffffff", fg="#1669a4").pack()
        Button(frame_convertir, text="Cargar archivo guardado del siges",
               command=convertir_xls_a_csv_arcos, font=("Helvetica Neue", 8)).pack(pady=5)

        # Estimador Manual
        frame_estimador_manual = tk.Frame(self.root, bg="#ffffff")
        frame_estimador_manual.pack(pady=10)
        tk.Label(frame_estimador_manual, text="Estimador Manual:", font=("Helvetica Neue", 9, "bold"),
                 bg="#ffffff", fg="#1669a4").pack()
        Button(frame_estimador_manual, text="Abrir Estimador Manual",
               command=Estimador_manual.crear_interfaz, font=("Helvetica Neue", 8)).pack(pady=5)

        

        # Extraer IPs
        frame_extraer_ips = tk.Frame(self.root, bg="#ffffff")
        frame_extraer_ips.pack(pady=10)
        tk.Label(frame_extraer_ips, text="Extraer rangos IP:", font=("Helvetica Neue", 9, "bold"),
                 bg="#ffffff", fg="#1669a4").pack()
        Button(frame_extraer_ips, text="Extraer IPs desde DBs",
               command=self.ejecutar_extraer_ips, font=("Helvetica Neue", 8)).pack(pady=5)

        Label(self.root, text="Hecho por: Iván Martínez", font=("Helvetica Neue", 7, "bold"),
              bg="#ffffff", fg="#1669a4").pack(pady=10, side=tk.BOTTOM)

    # -------------------- RUN --------------------

    def run(self) -> None:
        self.root.mainloop()


def main():
    app = AutoCSVApp()
    app.run()


if __name__ == "__main__":
    main()
