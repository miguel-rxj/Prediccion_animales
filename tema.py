"""Tema oscuro y componentes reutilizables de la interfaz Tkinter."""

import tkinter as tk
from tkinter import ttk


COLOR = {
    "fondo": "#0A0A0A", "tarjeta": "#141915", "elevado": "#202A22",
    "borde": "#344437", "foco": "#8EDD9B", "texto": "#EDEDED",
    "suave": "#B1BDB2", "acento": "#BCEBC2", "hover": "#D7F5DB",
    "tinta": "#112617", "aviso": "#F5CA80", "error": "#FF9995",
}
ESPACIO = {1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32}
RADIO = 12
TEXTO = ("Segoe UI", 11)
MONO = ("Consolas", 11)


def tema(raiz):
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure(".", font=TEXTO, background=COLOR["fondo"], foreground=COLOR["texto"])
    for nombre, fondo, tinta, hover, borde in [
        ("Primario", COLOR["acento"], COLOR["tinta"], COLOR["hover"], COLOR["acento"]),
        ("Secundario", COLOR["tarjeta"], COLOR["texto"], COLOR["elevado"], COLOR["borde"]),
        ("Navegacion", COLOR["tarjeta"], COLOR["suave"], COLOR["elevado"], COLOR["tarjeta"]),
        ("Actual", COLOR["elevado"], COLOR["acento"], COLOR["elevado"], COLOR["borde"]),
    ]:
        clase = f"{nombre}.TButton"
        estilo.configure(
            clase, background=fondo, foreground=tinta, bordercolor=borde, relief="flat",
            lightcolor=fondo, darkcolor=fondo, focuscolor=COLOR["foco"], focusthickness=2,
            padding=(ESPACIO[4], ESPACIO[2]), anchor="w" if nombre in {"Navegacion", "Actual"} else "center",
        )
        estilo.map(
            clase,
            background=[("disabled", COLOR["elevado"]), ("pressed", COLOR["borde"]), ("active", hover)],
            foreground=[("disabled", COLOR["suave"]), ("pressed", COLOR["texto"])],
            bordercolor=[("focus", COLOR["foco"])],
        )
    estilo.configure(
        "Referencia.Secundario.TButton", padding=(ESPACIO[2], ESPACIO[1]),
        background=COLOR["fondo"], lightcolor=COLOR["fondo"], darkcolor=COLOR["fondo"],
    )
    for clase in ("TEntry", "TCombobox"):
        estilo.configure(
            clase, padding=(ESPACIO[3], ESPACIO[2]), fieldbackground=COLOR["fondo"],
            foreground=COLOR["texto"], insertcolor=COLOR["texto"], bordercolor=COLOR["borde"],
            lightcolor=COLOR["fondo"], darkcolor=COLOR["fondo"], arrowcolor=COLOR["acento"],
            selectbackground=COLOR["borde"], selectforeground=COLOR["texto"],
        )
        estilo.map(
            clase, bordercolor=[("focus", COLOR["foco"])],
            fieldbackground=[("readonly", COLOR["fondo"])],
            foreground=[("readonly", COLOR["texto"])],
        )
    estilo.configure(
        "TRadiobutton", background=COLOR["tarjeta"], foreground=COLOR["texto"],
        indicatorbackground=COLOR["fondo"], indicatorforeground=COLOR["texto"],
        focuscolor=COLOR["foco"], padding=(0, ESPACIO[2]),
    )
    estilo.map(
        "TRadiobutton", background=[("active", COLOR["elevado"]), ("selected", COLOR["elevado"])],
        indicatorcolor=[("selected", COLOR["acento"])],
        indicatorbackground=[("selected", COLOR["acento"])], indicatorforeground=[("selected", COLOR["tinta"])],
    )
    estilo.configure(
        "Horizontal.TProgressbar", background=COLOR["acento"], troughcolor=COLOR["elevado"],
        bordercolor=COLOR["elevado"], lightcolor=COLOR["acento"], darkcolor=COLOR["acento"],
        thickness=8,
    )
    estilo.configure(
        "Treeview", font=MONO, rowheight=30, background=COLOR["tarjeta"], fieldbackground=COLOR["tarjeta"],
        foreground=COLOR["texto"], bordercolor=COLOR["borde"], relief="flat",
    )
    estilo.map(
        "Treeview", background=[("selected", COLOR["borde"])],
        foreground=[("selected", COLOR["texto"])], bordercolor=[("focus", COLOR["foco"])],
    )
    estilo.configure(
        "Treeview.Heading", background=COLOR["elevado"], foreground=COLOR["suave"],
        relief="flat", font=("Segoe UI", 10, "bold"), padding=(ESPACIO[2], ESPACIO[1]),
    )
    estilo.map("Treeview.Heading", background=[("active", COLOR["borde"])])
    for orientacion in ("Vertical", "Horizontal"):
        clase = f"{orientacion}.TScrollbar"
        elemento = f"{orientacion}.Scrollbar"
        direccion = "ns" if orientacion == "Vertical" else "ew"
        estilo.layout(clase, [
            (f"{elemento}.trough", {"sticky": direccion, "children": [
                (f"{elemento}.thumb", {"expand": True, "sticky": "nsew"}),
            ]}),
        ])
        estilo.configure(
            clase, background=COLOR["borde"], troughcolor=COLOR["fondo"],
            bordercolor=COLOR["fondo"], lightcolor=COLOR["borde"], darkcolor=COLOR["borde"],
            gripcount=0, width=10,
        )
        estilo.map(clase, background=[("active", COLOR["elevado"])])
    raiz.option_add("*TCombobox*Listbox.background", COLOR["elevado"])
    raiz.option_add("*TCombobox*Listbox.foreground", COLOR["texto"])
    raiz.option_add("*TCombobox*Listbox.selectBackground", COLOR["borde"])
    raiz.option_add("*TCombobox*Listbox.selectForeground", COLOR["texto"])
    raiz.option_add("*TCombobox*Listbox.font", TEXTO)


def texto(padre, contenido="", *, nivel="cuerpo", color="texto", ancho=640, variable=None):
    fuente = {
        "marca": ("Segoe UI", 21, "bold"), "hero": ("Segoe UI", 39, "bold"),
        "titulo": ("Segoe UI", 27, "bold"), "subtitulo": ("Segoe UI", 17, "bold"),
        "cuerpo": TEXTO, "detalle": ("Segoe UI", 10), "cifra": ("Consolas", 24, "bold"),
    }[nivel]
    return tk.Label(
        padre, text=contenido, textvariable=variable, bg=padre.cget("bg"), fg=COLOR[color],
        font=fuente, anchor="w", justify="left", wraplength=ancho, borderwidth=0,
        highlightthickness=0,
    )


def boton(padre, titulo, accion, estilo="Secundario", **opciones):
    return ttk.Button(padre, text=titulo, command=accion, style=f"{estilo}.TButton", **opciones)


class Tarjeta(tk.Canvas):
    """Superficie redondeada con un marco interior de controles nativos."""

    def __init__(self, padre, relleno=ESPACIO[6]):
        super().__init__(padre, bg=padre.cget("bg"), highlightthickness=0, borderwidth=0, width=1, height=1)
        self.relleno = relleno
        self.cuerpo = tk.Frame(self, bg=COLOR["tarjeta"])
        self.superficie = self.create_polygon(0, 0, 0, 0, fill=COLOR["tarjeta"], outline=COLOR["borde"])
        self.interior = self.create_window(relleno, relleno, anchor="nw", window=self.cuerpo)
        self.bind("<Configure>", self.ajustar)
        self.cuerpo.bind("<Configure>", self.ajustar_altura)

    def ajustar(self, evento):
        ancho = evento.width - 1
        alto = evento.height - 1
        r = min(RADIO, ancho / 2, alto / 2)
        self.coords(
            self.superficie, r, 0, ancho-r, 0, ancho, 0, ancho, r, ancho, alto-r,
            ancho, alto, ancho-r, alto, r, alto, 0, alto, 0, alto-r, 0, r, 0, 0,
        )
        self.itemconfigure(self.superficie, smooth=True, splinesteps=12)
        self.itemconfigure(self.interior, width=max(1, evento.width - 2 * self.relleno))
        self.ajustar_altura()

    def ajustar_altura(self, _evento=None):
        altura = self.cuerpo.winfo_reqheight() + 2 * self.relleno
        if int(self.cget("height")) != altura:
            self.configure(height=altura)


class VistaDesplazable(tk.Frame):
    def __init__(self, padre):
        super().__init__(padre, bg=COLOR["fondo"])
        self.lienzo = tk.Canvas(self, bg=COLOR["fondo"], highlightthickness=0, borderwidth=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.contenido = tk.Frame(self.lienzo, bg=COLOR["fondo"])
        self.ventana = self.lienzo.create_window(0, 0, anchor="nw", window=self.contenido)
        self.contenido.bind("<Configure>", self.actualizar_region)
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self.ventana, width=e.width))
        padre.bind("<MouseWheel>", self.rueda, add="+")
        padre.bind("<Button-4>", self.rueda, add="+")
        padre.bind("<Button-5>", self.rueda, add="+")
        padre.bind("<FocusIn>", self.mostrar_foco, add="+")

    def actualizar_region(self, _evento=None):
        self.lienzo.configure(scrollregion=self.lienzo.bbox(self.ventana))

    def rueda(self, evento):
        if str(evento.widget).startswith(str(self.contenido) + ".") and not isinstance(evento.widget, ttk.Treeview):
            avance = -1 if evento.num == 4 or evento.delta > 0 else 1
            self.lienzo.yview_scroll(avance * 2, "units")

    def mostrar_foco(self, evento):
        control = evento.widget
        if not str(control).startswith(str(self.contenido) + "."):
            return
        alto = self.contenido.winfo_height()
        if alto <= 1:
            return
        arriba = control.winfo_rooty() - self.contenido.winfo_rooty()
        abajo = arriba + control.winfo_height()
        visible_arriba = self.lienzo.canvasy(0)
        visible_abajo = visible_arriba + self.lienzo.winfo_height()
        if arriba < visible_arriba:
            self.lienzo.yview_moveto(max(0, arriba - ESPACIO[2]) / alto)
        elif abajo > visible_abajo:
            destino = abajo - self.lienzo.winfo_height() + ESPACIO[2]
            self.lienzo.yview_moveto(destino / alto)


def tabla(padre, columnas, titulos, anchos, altura=8, numericas=()):
    contenedor = tk.Frame(padre, bg=COLOR["tarjeta"])
    contenedor.columnconfigure(0, weight=1)
    contenedor.rowconfigure(0, weight=1)
    arbol = ttk.Treeview(contenedor, columns=columnas, show="headings", height=altura, selectmode="browse")
    vertical = ttk.Scrollbar(contenedor, orient="vertical", command=arbol.yview)
    horizontal = ttk.Scrollbar(contenedor, orient="horizontal", command=arbol.xview)
    arbol.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    arbol.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    for columna, titulo, ancho in zip(columnas, titulos, anchos):
        lado = "e" if columna in numericas else "w"
        arbol.heading(columna, text=titulo, anchor=lado)
        arbol.column(columna, width=ancho, minwidth=min(ancho, 80), anchor=lado, stretch=False)
    return contenedor, arbol
