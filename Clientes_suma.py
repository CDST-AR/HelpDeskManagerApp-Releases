import numpy as np
import pandas as pd
from tkinter import filedialog, simpledialog, messagebox
from datetime import datetime

def convertir_xls_a_csv_arcos():
    archivo_xls = filedialog.askopenfilename(title="Selecciona un archivo XLS", filetypes=[("Archivos XLS", "*.xls *.xlsx")])
    if not archivo_xls:
        return

    datos = pd.read_excel(archivo_xls)
    datos.rename(columns={'Nro Serie': 'SERIE'}, inplace=True)

    columnas_a_eliminar = ['Empresa', 'Centro Costo', 'CMeses', 'Conts', 'Bonif', 'Renta', 
                           'Diferencia', 'Clase', 'Modelo', 'Sector', 'Direccion IP', 
                           'Toma Anterior', 'Toma Actual', 'Cdor Anterior', 'Tipo', 'Tipo.1']
    datos.drop(columns=columnas_a_eliminar, errors='ignore', inplace=True)

    fecha_usuario = simpledialog.askstring("Entrada de Fecha", "Ingrese la fecha (DD/MM/AAAA):")
    if not fecha_usuario:
        messagebox.showwarning("Advertencia", "No se ingresó ninguna fecha.")
        return
    
    try:
        fecha_actual = datetime.strptime(fecha_usuario, '%d/%m/%Y').strftime('%d/%m/%Y')
        messagebox.showinfo("Fecha ingresada", "La fecha se ha ingresado correctamente.")
    except ValueError:
        messagebox.showerror("Error", "La fecha ingresada no tiene el formato correcto (DD/MM/AAAA).")
        return
    
    datos['FECHA'] = fecha_actual
    datos['TIPO'] = "14"
    datos['CLASE'] = "10"
    datos['CONTADOR'] = ""
    
    hojas_a_sumar = simpledialog.askinteger("Copias a sumar", "Ingrese la cantidad de hojas que desea sumar a los equipos a estimar:")
    if hojas_a_sumar is None:
        messagebox.showwarning("Advertencia", "No se ingresó ninguna cantidad. Los equipos a estimar no serán modificados.")
        hojas_a_sumar = 0
    

    datos['CONTADOR'] = np.where((datos['Estado'] == 'Desaparecida') | (datos['Estado'] == 'Backup Fijo'), datos['Cdor Actual'],
                                 np.where(datos['Cdor Actual'] == 1, datos['Cdor Actual'],
                                          np.where((datos['Estado'] == 'Activa en Cliente') & (datos['Cdor Actual'] != 1),
                                                   datos['Cdor Actual'] + hojas_a_sumar, '')))

    if 'SERIE' in datos.columns:  
        indice_serie = datos.columns.get_loc('SERIE')
        columnas = datos.columns.tolist()
        columnas.remove('FECHA')
        columnas.remove('TIPO')
        columnas.remove('CLASE')
        columnas.remove('CONTADOR')
        columnas.insert(indice_serie + 1, 'FECHA')
        columnas.insert(indice_serie + 2, 'TIPO')
        columnas.insert(indice_serie + 3, 'CLASE')
        columnas.insert(indice_serie + 4, 'CONTADOR')
        datos = datos[columnas]
    
    archivo_csv = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Archivos CSV", "*.csv")])
    if archivo_csv:
        datos.to_csv(archivo_csv, index=False, sep=';')
        messagebox.showinfo("Éxito", f"Archivo CSV guardado exitosamente en: {archivo_csv}")
