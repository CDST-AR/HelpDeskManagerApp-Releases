import tkinter as tk
from tkinter import ttk
from datetime import datetime
import math

def calcular_dias360(fecha_inicial, fecha_final):
    dia_inicial, mes_inicial, ano_inicial = fecha_inicial.day, fecha_inicial.month, fecha_inicial.year
    dia_final, mes_final, ano_final = fecha_final.day, fecha_final.month, fecha_final.year

    if dia_inicial == 31:
        dia_inicial = 30
    if dia_final == 31 and dia_inicial >= 30:
        dia_final = 30

    dias360 = (ano_final - ano_inicial) * 360 + (mes_final - mes_inicial) * 30 + (dia_final - dia_inicial)
    return dias360

def calcular_impresiones_mensuales(impresiones_diarias, entry_impresiones_mensuales):
    impresiones_mensuales = round(impresiones_diarias * 30, 2)

    entry_impresiones_mensuales.config(state=tk.NORMAL)
    entry_impresiones_mensuales.delete(0, tk.END)
    entry_impresiones_mensuales.insert(0, str(impresiones_mensuales))
    entry_impresiones_mensuales.config(state='readonly')

def calcular_resultado_estimacion(contador_final, impresiones_diarias, num_dias_estimacion, entry_contador_estimado, entry_impresiones_estimadas):
    contador_estimado = math.ceil(contador_final + (impresiones_diarias * num_dias_estimacion))
    impresiones_estimadas = math.ceil(impresiones_diarias * num_dias_estimacion)

    entry_contador_estimado.config(state=tk.NORMAL)
    entry_contador_estimado.delete(0, tk.END)
    entry_contador_estimado.insert(0, str(contador_estimado))
    entry_contador_estimado.config(state='readonly')

    entry_impresiones_estimadas.config(state=tk.NORMAL)
    entry_impresiones_estimadas.delete(0, tk.END)
    entry_impresiones_estimadas.insert(0, str(impresiones_estimadas))
    entry_impresiones_estimadas.config(state='readonly')

def calcular_impresiones_diarias(entry_contador_inicial, entry_contador_final, entry_fecha_inicial, entry_fecha_final, entry_fecha_estimacion, entry_impresiones_diarias, entry_dias_estimacion, entry_impresiones_mensuales, entry_contador_estimado, entry_impresiones_estimadas):
    contador_inicial = int(entry_contador_inicial.get())
    contador_final = int(entry_contador_final.get())
    fecha_inicial = entry_fecha_inicial.get()
    fecha_final = entry_fecha_final.get()
    fecha_estimacion = entry_fecha_estimacion.get()

    fecha_inicial = datetime.strptime(fecha_inicial, "%d/%m/%Y")
    fecha_final = datetime.strptime(fecha_final, "%d/%m/%Y")
    fecha_estimacion = datetime.strptime(fecha_estimacion, "%d/%m/%Y")

    num_dias = calcular_dias360(fecha_inicial, fecha_final)
    num_dias_estimacion = calcular_dias360(fecha_final, fecha_estimacion)

    impresiones_diarias = round((contador_final - contador_inicial) / num_dias, 2)

    entry_impresiones_diarias.config(state=tk.NORMAL)
    entry_impresiones_diarias.delete(0, tk.END)
    entry_impresiones_diarias.insert(0, str(impresiones_diarias))
    entry_impresiones_diarias.config(state='readonly')

    entry_dias_estimacion.config(state=tk.NORMAL)
    entry_dias_estimacion.delete(0, tk.END)
    entry_dias_estimacion.insert(0, str(num_dias_estimacion))
    entry_dias_estimacion.config(state='readonly')

    calcular_impresiones_mensuales(impresiones_diarias, entry_impresiones_mensuales)
    calcular_resultado_estimacion(contador_final, impresiones_diarias, num_dias_estimacion, entry_contador_estimado, entry_impresiones_estimadas)

def crear_interfaz():
    root = tk.Tk()
    root.title("Estimador Manual")
    root.configure(bg="#ffffff")

    font = ("Helvetica Neue", 9, "bold")
    font_title = ("Helvetica Neue", 16, "bold")

    style = ttk.Style()
    style.configure("TLabel", font=font, background="#ffffff", foreground="#1669a4")
    style.configure("TFrame", background="#ffffff")
    style.configure("TButton", font=font, background="#ffffff", foreground="#1669a4")
    style.configure("TEntry", font=font, foreground="#1669a4")

    style.configure("TLabel", foreground="#f4951f")
    style.map("TLabel", foreground=[("selected", "#f4951f")])

    # Crear un Label para el título principal
    title_label = tk.Label(root, text="Estimación manual de contadores", font=font_title, bg="#ffffff", fg="#f4951f")
    title_label.pack(pady=10)

    # Contador inicial
    frame_contador_inicial = tk.Frame(root, bd=2, relief=tk.GROOVE, bg="#ffffff")
    frame_contador_inicial.pack(padx=10, pady=10)

    label_fecha_proceso = tk.Label(frame_contador_inicial, text="Primer contador real", bg="#ffffff", fg="#f4951f", font=font)
    label_fecha_proceso.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

    label_fecha_inicial = tk.Label(frame_contador_inicial, text="Fecha (dd/mm/yyyy):", bg="#ffffff", fg="#1669a4", font=font)
    label_fecha_inicial.grid(row=1, column=0, padx=5, pady=5)

    entry_fecha_inicial = tk.Entry(frame_contador_inicial, font=font, bg="#ffffff", fg="#1669a4")
    entry_fecha_inicial.grid(row=1, column=1, padx=5, pady=5)

    label_contador_inicial = tk.Label(frame_contador_inicial, text="Contador:", bg="#ffffff", fg="#1669a4", font=font)
    label_contador_inicial.grid(row=2, column=0, padx=5, pady=5)

    entry_contador_inicial = tk.Entry(frame_contador_inicial, font=font, bg="#ffffff", fg="#1669a4")
    entry_contador_inicial.grid(row=2, column=1, padx=5, pady=5)

    # Contador final
    frame_contador_final = tk.Frame(root, bd=2, relief=tk.GROOVE, bg="#ffffff")
    frame_contador_final.pack(padx=10, pady=10)

    label_fecha_proceso = tk.Label(frame_contador_final, text="Ultimo contador real", bg="#ffffff", fg="#f4951f", font=font)
    label_fecha_proceso.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

    label_fecha_final = tk.Label(frame_contador_final, text="Fecha (dd/mm/yyyy):", bg="#ffffff", fg="#1669a4", font=font)
    label_fecha_final.grid(row=1, column=0, padx=5, pady=5)

    entry_fecha_final = tk.Entry(frame_contador_final, font=font, bg="#ffffff", fg="#1669a4")
    entry_fecha_final.grid(row=1, column=1, padx=5, pady=5)

    label_contador_final = tk.Label(frame_contador_final, text="Contador:", bg="#ffffff", fg="#1669a4", font=font)
    label_contador_final.grid(row=2, column=0, padx=5, pady=5)

    entry_contador_final = tk.Entry(frame_contador_final, font=font, bg="#ffffff", fg="#1669a4")
    entry_contador_final.grid(row=2, column=1, padx=5, pady=5)

    # Datos Estimación
    frame_datos_estimacion = tk.Frame(root, bd=2, relief=tk.GROOVE, bg="#ffffff")
    frame_datos_estimacion.pack(padx=10, pady=10)

    label_fecha_proceso = tk.Label(frame_datos_estimacion, text="Fecha de proceso", bg="#ffffff", fg="#f4951f", font=font)
    label_fecha_proceso.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

    label_fecha_estimacion = tk.Label(frame_datos_estimacion, text="Fecha (dd/mm/yyyy):", bg="#ffffff", fg="#1669a4", font=font)
    label_fecha_estimacion.grid(row=1, column=0, padx=5, pady=5)

    entry_fecha_estimacion = tk.Entry(frame_datos_estimacion, font=font, bg="#ffffff", fg="#1669a4")
    entry_fecha_estimacion.grid(row=1, column=1, padx=5, pady=5)

    label_dias = tk.Label(frame_datos_estimacion, text="Días:", bg="#ffffff", fg="#1669a4", font=font)
    label_dias.grid(row=2, column=0, padx=5, pady=5)

    entry_dias_estimacion = tk.Entry(frame_datos_estimacion, font=font, bg="#ffffff", fg="#1669a4", state='readonly')
    entry_dias_estimacion.grid(row=2, column=1, padx=5, pady=5)

    # Botón para calcular impresiones diarias
    tk.Button(root, text="Calcular Impresiones", command=lambda: calcular_impresiones_diarias(entry_contador_inicial, entry_contador_final, entry_fecha_inicial, entry_fecha_final, entry_fecha_estimacion, entry_impresiones_diarias, entry_dias_estimacion, entry_impresiones_mensuales, entry_contador_estimado, entry_impresiones_estimadas)).pack(pady=20)

    # Campo para mostrar las impresiones diarias
    frame_impresiones_diarias = tk.Frame(root, bd=2, relief=tk.GROOVE, bg="#ffffff")
    frame_impresiones_diarias.pack(padx=10, pady=10)

    label_impresiones_diarias = tk.Label(frame_impresiones_diarias, text="Impresiones Diarias:", bg="#ffffff", fg="#1669a4", font=font)
    label_impresiones_diarias.grid(row=0, column=0)

    entry_impresiones_diarias = tk.Entry(frame_impresiones_diarias, font=font, bg="#ffffff", fg="#1669a4", state='readonly')
    entry_impresiones_diarias.grid(row=0, column=1)

    label_impresiones_mensuales = tk.Label(frame_impresiones_diarias, text="Impresiones Mensuales:", bg="#ffffff", fg="#1669a4", font=font)
    label_impresiones_mensuales.grid(row=1, column=0)

    entry_impresiones_mensuales = tk.Entry(frame_impresiones_diarias, font=font, bg="#ffffff", fg="#1669a4", state='readonly')
    entry_impresiones_mensuales.grid(row=1, column=1)

    label_contador_estimado = tk.Label(frame_impresiones_diarias, text="Contador Estimado:", bg="#ffffff", fg="#1669a4", font=font)
    label_contador_estimado.grid(row=2, column=0)

    entry_contador_estimado = tk.Entry(frame_impresiones_diarias, font=font, bg="#ffffff", fg="#1669a4", state='readonly')
    entry_contador_estimado.grid(row=2, column=1)

    label_impresiones_estimadas = tk.Label(frame_impresiones_diarias, text="Impresiones Estimadas:", bg="#ffffff", fg="#1669a4", font=font)
    label_impresiones_estimadas.grid(row=3, column=0)

    entry_impresiones_estimadas = tk.Entry(frame_impresiones_diarias, font=font, bg="#ffffff", fg="#1669a4", state='readonly')
    entry_impresiones_estimadas.grid(row=3, column=1)

    root.lift()  # Elevar la ventana al frente
    root.attributes('-topmost', True)  # Establecer la ventana como la superior

    
    root.mainloop()

if __name__ == "__main__":
    crear_interfaz()

