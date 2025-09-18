import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog, simpledialog, messagebox

# === Importá tus módulos/funciones actuales aquí ===
from Db3ToCsv import procesar_db3_a_csv
from CsvEn0 import filtrar_falta_contador_csv
import Estimador_manual
from Clientes_suma import convertir_xls_a_csv_arcos
from Extraer_ips import generate_ip_ranges
import Updater

APP_NAME = "HelpDeskManagerApp"    
APP_VERSION = "v1.0.1"

class HelpDeskManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}")
        self.geometry("460x420")
        self.minsize(460, 380)
        self.configure(padx=10, pady=10)

        # Estilos ttk
        self._setup_style()

        # Layout base: Header / Notebook / Statusbar
        self._build_header()
        self._build_notebook()
        self._build_statusbar()

        # Menú superior
        self._build_menu()

        # Atajos
        self.bind_all("<Control-q>", lambda e: self.quit())
        self.bind_all("<F1>", lambda e: self._about())

        # Chequeo silencioso 2 segundos después de abrir la ventana
        self.after(2000, lambda: Updater.auto_check(self, APP_VERSION))

    # ---------- UI builders ----------
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Colores
        ORANGE = "#FF7F00"
        BLUE = "#1E90FF"
        BG = "#FFFFFF"
        TEXT = "#333333"

        # Fondo global
        self.configure(bg=BG)

        # Frames y Labels
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=ORANGE, background=BG)
        style.configure("Sub.TLabel", foreground=BLUE, background=BG)

        # Labelframe con fondo blanco
        style.configure("Card.TLabelframe", background=BG, relief="groove", borderwidth=1)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground=TEXT, background=BG)

        # Botones con hover naranja
        style.configure("Big.TButton", font=("Segoe UI", 10), padding=(10, 8), background=BG, foreground=TEXT)
        style.map("Big.TButton",
                background=[("active", ORANGE)],
                foreground=[("active", "white")])

        # Notebook fondo blanco y pestañas naranjas al seleccionar
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(10, 5), background=BG)
        style.map("TNotebook.Tab",
                background=[("selected", ORANGE)],
                foreground=[("selected", "white")])

    def _build_header(self):
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=APP_NAME, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Gestión de mesa de ayuda • Operaciones", style="Sub.TLabel")\
           .grid(row=1, column=0, sticky="w", pady=(2, 8))

        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=(6, 8))

    def _build_notebook(self):
        self.nb = ttk.Notebook(self)
        self.nb.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # Tabs
        self.tab_contadores = ttk.Frame(self.nb, padding=(4, 8))
        self.tab_stc = ttk.Frame(self.nb, padding=(4, 8))

        self.nb.add(self.tab_contadores, text="Contadores")
        self.nb.add(self.tab_stc, text="STC")

        # Pestaña: Contadores
        self._build_tab_contadores(self.tab_contadores)

        # Pestaña: STC
        self._build_tab_stc(self.tab_stc)

    def _build_statusbar(self):
        self.status = tk.StringVar(value="Listo")
        bar = ttk.Frame(self)
        bar.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        bar.columnconfigure(0, weight=1)
        ttk.Separator(bar, orient="horizontal").grid(row=0, column=0, sticky="ew")
        ttk.Label(bar, textvariable=self.status, anchor="w").grid(row=1, column=0, sticky="ew", pady=(4, 2))

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        archivo = tk.Menu(menubar, tearoff=0)
        archivo.add_command(label="Salir (Ctrl+Q)", command=self.quit)
        menubar.add_cascade(label="Archivo", menu=archivo)

        ayuda = tk.Menu(menubar, tearoff=0)
        ayuda.add_command(label="Acerca de (F1)", command=self._about)
        ayuda.add_command(
        label="Buscar actualizaciones…",
        command=lambda: Updater.check_for_updates(self, app_version=APP_VERSION)
    )
        menubar.add_cascade(label="Ayuda", menu=ayuda)

    # ---------- Contenido de pestañas ----------
    def _build_tab_contadores(self, parent):
        parent.columnconfigure(0, weight=1)

        card = ttk.Labelframe(parent, text="Operaciones de Contadores", style="Card.TLabelframe")
        card.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Configurar 2 columnas con el mismo ancho
        card.columnconfigure(0, weight=1, uniform="cols")
        card.columnconfigure(1, weight=1, uniform="cols")

        # Fila 1
        ttk.Button(
            card, text="Procesar\nDB3 → CSV",
            style="Big.TButton", command=self._procesar_archivos
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        ttk.Button(
            card, text="Estimación en 0\nContadores por Proceso",
            style="Big.TButton", command=self._contadores_por_proceso
        ).grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        # Fila 2
        ttk.Button(
            card, text="Estimación\nsuma fija",
            style="Big.TButton", command=self._estimacion_suma_fija
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=8)

        ttk.Button(
            card, text="Abrir\nEstimador Manual",
            style="Big.TButton", command=self._abrir_estimador_manual
        ).grid(row=1, column=1, sticky="ew", padx=8, pady=8)

        # Pie
        ttk.Label(parent, text="Hecho por: Iván Martínez", style="Sub.TLabel")\
            .grid(row=1, column=0, sticky="w", padx=6, pady=(4, 0))

    def _build_tab_stc(self, parent):
        parent.columnconfigure(0, weight=1)
        card_net = ttk.Labelframe(parent, text="Herramientas STC", style="Card.TLabelframe")
        card_net.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        card_net.columnconfigure(0, weight=1)

        ttk.Button(card_net, text="Generar Direcciones IP",
                   style="Big.TButton", command=self._generar_ips)\
            .grid(row=0, column=0, sticky="ew", padx=6, pady=6)

    # ---------- Acciones (conecta aquí tus funciones reales) ----------
    def _run_action(self, label, fn):
        self.status.set(f"Ejecutando: {label}…")
        self.update_idletasks()
        try:
            fn()
            self.status.set(f"✔ {label} completado")
        except Exception as e:
            self.status.set(f"✖ Error en {label}")
            messagebox.showerror("Error", f"Ocurrió un error en '{label}':\n\n{e}")

    # Contadores
    def _procesar_archivos(self):
        def _do():
            try:
                archivos = filedialog.askopenfilenames(
                    title="Selecciona archivos DB3",
                    filetypes=[("Base de datos DB3", "*.db3")],
                    parent=self
                )
                if not archivos:
                    return

                fecha_max = simpledialog.askstring(
                    "Fecha máxima",
                    "Ingrese fecha máxima (YYYY-MM-DD) o deje vacío para omitir:",
                    parent=self
                )
                if fecha_max == "":
                    fecha_max = None

                nombre_base = simpledialog.askstring(
                    "Nombre base",
                    "Ingrese el prefijo para el CSV:",
                    parent=self
                )
                if not nombre_base:
                    return

                carpeta_destino = filedialog.askdirectory(
                    title="Selecciona carpeta de destino",
                    parent=self
                )
                if not carpeta_destino:
                    carpeta_destino = None  # usa carpeta del primer DB3

                # --- Llamada a la función del módulo separado ---
                ruta_salida = procesar_db3_a_csv(
                    archivos_db3=archivos,
                    fecha_maxima=fecha_max,
                    nombre_base_salida=nombre_base,
                    carpeta_salida=carpeta_destino
                )

                messagebox.showinfo("Éxito", f"CSV generado en:\n{ruta_salida}", parent=self)

            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un problema:\n{e}", parent=self)

        self._run_action("Procesar archivos CSV", _do)

    def _contadores_por_proceso(self):
        def _do():
            try:
                # 1. Seleccionar CSV de entrada
                archivo_csv = filedialog.askopenfilename(
                    title="Selecciona archivo CSV",
                    filetypes=[("Archivos CSV", "*.csv")],
                    parent=self
                )
                if not archivo_csv:
                    return  # cancelado

                # 2. Pedir fecha
                fecha_nueva = simpledialog.askstring(
                    "Fecha", "Ingrese la fecha (DD/MM/YYYY):", parent=self
                )
                if not fecha_nueva:
                    return  # cancelado

                # 3. Pedir nombre de cliente
                nombre_cliente = simpledialog.askstring(
                    "Cliente", "Ingrese el nombre del cliente:", parent=self
                )
                if not nombre_cliente:
                    return  # cancelado

                # 4. Carpeta de salida
                carpeta_salida = filedialog.askdirectory(
                    title="Selecciona carpeta de destino", parent=self
                )
                if not carpeta_salida:
                    carpeta_salida = None  # usa la del archivo CSV

                # 5. Ejecutar la función del módulo
                ruta_salida = filtrar_falta_contador_csv(
                    archivo_csv_entrada=archivo_csv,
                    fecha_nueva=fecha_nueva,
                    nombre_cliente=nombre_cliente,
                    carpeta_salida=carpeta_salida
                )

                # 6. Aviso final
                messagebox.showinfo("Éxito", f"CSV generado en:\n{ruta_salida}", parent=self)

            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un problema:\n{e}", parent=self)

        self._run_action("Cargar CSV: Contadores por Proceso", _do)

    def _estimacion_suma_fija(self):
        def _do():
            # Llama directo a tu módulo (abre diálogos, lee XLS/XLSX y guarda CSV)
            convertir_xls_a_csv_arcos()
        self._run_action("Estimación con suma fija (SIGES)", _do)

    def _abrir_estimador_manual(self):
        def _do():
            Estimador_manual.crear_interfaz()  # o el nombre que use tu módulo para abrir la UI
        self._run_action("Abrir Estimador Manual", _do)


    # STC
    def _generar_ips(self):
        def _do():
            try:
                # Si querés forzar rutas o la carpeta de guardado, podés pasarlas:
                # out_path, count = generate_ip_ranges(paths=[...], save_path="C:/destino/salida.txt")
                out_path, count = generate_ip_ranges()  # usa los diálogos del módulo
                if count:
                    messagebox.showinfo("Direcciones IP",
                                        f"Se guardaron {count} rango(s) /24 en:\n{out_path}",
                                        parent=self)
                else:
                    messagebox.showinfo("Direcciones IP",
                                        f"No se encontraron IPv4 válidas.\nSe generó archivo vacío en:\n{out_path}",
                                        parent=self)
            except Exception as e:
                messagebox.showerror("Error al generar IPs", str(e), parent=self)

        self._run_action("Generar Direcciones IP", _do)

    # ----------
    def _about(self):
        messagebox.showinfo(
            "Acerca de",
            f"{APP_NAME} {APP_VERSION}\n\nOrganiza herramientas por áreas (Contadores / STC).\nHecho por: Iván Martínez."
        )

if __name__ == "__main__":
    app = HelpDeskManagerApp()
    app.mainloop()
