"""Punto de entrada e interfaz de escritorio de Animal AI."""

import logging
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import messagebox, ttk

from servicios import (
    CARACTERISTICAS, CLASE, ETIQUETAS, MINIMO_RECOMENDADO, PESO,
    ErrorAnimal, RepositorioDataset, ServicioModelo, clave, leer_peso, mostrar,
    mostrar_peso, opciones, valor_canonico,
)
from tema import COLOR, ESPACIO, Tarjeta, VistaDesplazable, boton, tabla, tema, texto


PREGUNTAS = {
    PESO: "¿Cuánto pesa aproximadamente el animal?",
    "tiene_pelaje": "¿Tiene pelaje?",
    "habitat": "¿En qué hábitat vive?",
    "alimentacion": "¿Qué tipo de alimentación tiene?",
    "sonido": "¿Qué sonido realiza?",
    "tiene_patas": "¿Tiene patas?",
}
PESOS_RAPIDOS = [
    ("Luciérnaga", "0,00002"), ("Ratón", "0,025"), ("Conejo", "2"),
    ("Perro mediano", "20"), ("Caballo", "500"), ("Elefante", "5000"),
]
UMBRAL_DUDA = 0.60
COLUMNAS_TABLA = [CLASE, *CARACTERISTICAS]
ANCHO_COLUMNAS = (130, 108, 126, 160, 125, 115, 120)


def porcentaje(valor):
    return f"{valor:.1%}".replace(".", ",").replace("%", " %")


def formato_celda(columna, valor):
    return mostrar_peso(valor) if columna == PESO else mostrar(valor)


def etiquetas_opciones(valores):
    """Devuelve etiquetas únicas para conservar las categorías exactas del CSV."""
    etiquetas = {}
    for valor in valores:
        etiqueta = mostrar(valor)
        while etiqueta in etiquetas and etiquetas[etiqueta] != valor:
            etiqueta += f" ({valor})"
        etiquetas[etiqueta] = valor
    return etiquetas


class AnimalAI:
    def __init__(self, raiz, carpeta):
        self.raiz = raiz
        self.repositorio = RepositorioDataset(carpeta / "dataset_animales_clasificacion.csv")
        self.servicio = ServicioModelo(carpeta / "modelo_animales.pkl")
        self.datos = None
        self.modelo = None
        self.error_csv = ""
        self.error_modelo = ""
        self.paso = 0
        self.respuestas = {columna: tk.StringVar(raiz) for columna in CARACTERISTICAS}
        self.campos = {columna: tk.StringVar(raiz) for columna in COLUMNAS_TABLA}
        self.pendientes = []
        self.resultado = None
        self.informe = None
        self.entrenando = False
        self.estado_entrenamiento = ""
        self.cola_entrenamiento = Queue()
        self.pagina = ""
        self.cargar_dataset()
        self.cargar_modelo()
        self.construir_ventana()
        self.ir("inicio")

    def cargar_dataset(self):
        try:
            self.datos = self.repositorio.leer()
            self.error_csv = ""
        except ErrorAnimal as error:
            self.datos = None
            self.error_csv = str(error)

    def cargar_modelo(self):
        try:
            self.modelo = self.servicio.cargar(self.datos)
            self.error_modelo = ""
        except ErrorAnimal as error:
            self.modelo = None
            self.error_modelo = str(error)

    def construir_ventana(self):
        self.raiz.title("Animal AI · Clasificación de animales")
        self.raiz.geometry("1160x760")
        self.raiz.minsize(820, 540)
        self.raiz.configure(bg=COLOR["fondo"])
        self.raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        tema(self.raiz)
        self.raiz.rowconfigure(0, weight=1)
        self.raiz.columnconfigure(1, weight=1)
        lateral = tk.Frame(self.raiz, bg=COLOR["tarjeta"], padx=ESPACIO[4], pady=ESPACIO[8])
        lateral.grid(row=0, column=0, sticky="ns")
        texto(lateral, "Animal AI", nivel="marca", color="acento").pack(anchor="w")
        texto(lateral, "Clasificador de animales", nivel="detalle", color="suave").pack(anchor="w")
        nav = tk.Frame(lateral, bg=COLOR["tarjeta"])
        nav.pack(fill="x", pady=(ESPACIO[8], 0))
        self.navegacion = {}
        for pagina, titulo in [
            ("inicio", "Inicio"), ("quiz", "Adivinar animal"), ("registro", "Registrar animal"),
            ("dataset", "Dataset"), ("entrenamiento", "Reentrenar modelo"),
        ]:
            control = boton(nav, titulo, lambda destino=pagina: self.ir(destino), "Navegacion")
            control.pack(fill="x", pady=(0, ESPACIO[1]))
            self.navegacion[pagina] = control
        self.vista = VistaDesplazable(self.raiz)
        self.vista.grid(row=0, column=1, sticky="nsew")
        self.area = tk.Frame(self.vista.contenido, bg=COLOR["fondo"], padx=ESPACIO[8], pady=ESPACIO[6])
        self.area.pack(fill="x")

    def ir(self, pagina, *, arriba=True):
        self.pagina = pagina
        for control in self.area.winfo_children():
            control.destroy()
        activo = "quiz" if pagina == "resultado" else pagina
        for destino, control in self.navegacion.items():
            control.configure(style="Actual.TButton" if destino == activo else "Navegacion.TButton")
        vistas = {
            "inicio": self.inicio, "quiz": self.cuestionario, "resultado": self.mostrar_resultado,
            "registro": self.registro, "dataset": self.dataset, "entrenamiento": self.entrenamiento,
        }
        vistas[pagina]()
        if arriba:
            self.vista.lienzo.yview_moveto(0)

    def cabecera(self, titulo, descripcion):
        texto(self.area, titulo, nivel="titulo").pack(anchor="w")
        texto(self.area, descripcion, color="suave", ancho=510).pack(
            anchor="w", pady=(ESPACIO[2], ESPACIO[6]),
        )

    def tarjeta(self, relleno=ESPACIO[6]):
        tarjeta = Tarjeta(self.area, relleno=relleno)
        tarjeta.pack(fill="x", pady=(0, ESPACIO[4]))
        return tarjeta.cuerpo

    def aviso_dataset(self):
        panel = self.tarjeta()
        texto(panel, "Dataset no disponible", nivel="subtitulo").pack(anchor="w")
        texto(panel, self.error_csv, color="error", ancho=500).pack(anchor="w", pady=ESPACIO[2])
        boton(panel, "Actualizar datos", self.actualizar_dataset, "Primario").pack(anchor="w", pady=(ESPACIO[2], 0))

    def inicio(self):
        hero = self.tarjeta()
        texto(hero, "Animal AI", nivel="hero").pack(anchor="w")
        texto(
            hero, "Responde seis preguntas sobre un animal y descubre cuál identifica el modelo.",
            color="suave", ancho=500,
        ).pack(anchor="w", pady=(ESPACIO[2], ESPACIO[6]))
        boton(hero, "Comenzar a identificar", lambda: self.ir("quiz"), "Primario").pack(anchor="w")
        metricas = tk.Frame(self.area, bg=COLOR["fondo"])
        metricas.pack(fill="x", pady=(0, ESPACIO[4]))
        estadisticas = [
            ("Animales reconocidos", str(len(self.modelo.classes_)) if self.modelo is not None else "—"),
            ("Registros en el dataset", str(len(self.datos)) if self.datos is not None else "—"),
            ("Estado del modelo", "Disponible" if self.modelo is not None else "Pendiente"),
        ]
        for indice, (etiqueta, valor) in enumerate(estadisticas):
            metricas.columnconfigure(indice, weight=1, uniform="metricas")
            tarjeta = Tarjeta(metricas, relleno=ESPACIO[4])
            tarjeta.grid(row=0, column=indice, sticky="nsew", padx=(0, ESPACIO[2] if indice < 2 else 0))
            texto(tarjeta.cuerpo, valor, nivel="subtitulo" if indice == 2 else "cifra", color="acento").pack(anchor="w")
            texto(tarjeta.cuerpo, etiqueta, nivel="detalle", color="suave", ancho=145).pack(
                anchor="w", pady=(ESPACIO[1], 0),
            )
        if self.error_modelo:
            panel = self.tarjeta()
            texto(panel, self.error_modelo, color="error", ancho=500).pack(anchor="w")
            boton(panel, "Volver a cargar el modelo", self.recargar_modelo).pack(anchor="w", pady=(ESPACIO[3], 0))
        if self.error_csv:
            self.aviso_dataset()

    def recargar_modelo(self):
        self.cargar_modelo()
        self.ir("inicio")

    def cuestionario(self):
        self.cabecera("Adivina el animal", "Describe el animal que tienes en mente.")
        if self.datos is None:
            self.aviso_dataset()
            return
        if self.datos.empty:
            panel = self.tarjeta()
            texto(panel, "El dataset está vacío. Registra ejemplos para disponer de opciones.").pack(anchor="w")
            boton(panel, "Registrar animal", lambda: self.ir("registro"), "Primario").pack(
                anchor="w", pady=(ESPACIO[3], 0),
            )
            return
        panel = self.tarjeta(relleno=ESPACIO[4])
        total = len(CARACTERISTICAS)
        resumen = self.paso == total
        etapa = "Revisión de respuestas" if resumen else f"Pregunta {self.paso + 1} de {total}"
        texto(panel, etapa, nivel="detalle", color="acento").pack(anchor="w")
        ttk.Progressbar(panel, maximum=total, value=self.paso, takefocus=False).pack(
            fill="x", pady=(ESPACIO[2], ESPACIO[4]),
        )
        error_resumen = ""
        if resumen:
            texto(panel, "Revisa tus respuestas", nivel="subtitulo").pack(anchor="w", pady=(0, ESPACIO[4]))
            try:
                self.detalles(panel, self.obtener_respuestas())
            except ErrorAnimal:
                error_resumen = "Las opciones del dataset cambiaron. Retrocede y revisa tus respuestas."
        else:
            columna = CARACTERISTICAS[self.paso]
            texto(panel, PREGUNTAS[columna], nivel="subtitulo", ancho=510).pack(anchor="w", pady=(0, ESPACIO[3]))
            self.control_pregunta(panel, columna)
        mensaje = error_resumen or (self.error_modelo if resumen and self.modelo is None else "")
        self.error_quiz = tk.StringVar(self.raiz, value=mensaje)
        aviso = texto(panel, color="error", variable=self.error_quiz, ancho=490)
        acciones = tk.Frame(panel, bg=COLOR["tarjeta"])
        acciones.pack(fill="x", pady=(ESPACIO[4], 0))

        def mostrar_aviso(*_):
            if self.error_quiz.get():
                aviso.pack(before=acciones, anchor="w", pady=(ESPACIO[3], 0))
            else:
                aviso.pack_forget()

        self.error_quiz.trace_add("write", mostrar_aviso)
        mostrar_aviso()
        boton(acciones, "Reiniciar", self.reiniciar).pack(side="left")
        anterior = boton(acciones, "Anterior", lambda: self.cambiar_paso(-1))
        anterior.pack(side="left", padx=ESPACIO[2])
        if self.paso == 0:
            anterior.state(["disabled"])
        if resumen:
            adivinar = boton(acciones, "Adivinar animal", self.predecir, "Primario")
            adivinar.pack(side="right")
            if self.modelo is None or error_resumen:
                adivinar.state(["disabled"])
        else:
            boton(acciones, "Siguiente", self.siguiente, "Primario").pack(side="right")

    def control_pregunta(self, panel, columna):
        respuesta = self.respuestas[columna]
        if columna == PESO:
            texto(panel, "Peso en kilogramos (kg)", nivel="detalle", color="suave").pack(anchor="w")
            campo = ttk.Entry(panel, textvariable=respuesta)
            campo.pack(fill="x", pady=(ESPACIO[1], ESPACIO[2]))
            campo.bind("<Return>", lambda _: self.siguiente())
            texto(panel, "Escribe un valor o usa una referencia aproximada.", color="suave").pack(
                anchor="w", pady=(0, ESPACIO[3]),
            )
            rejilla = tk.Frame(panel, bg=COLOR["tarjeta"])
            rejilla.pack(fill="x")
            for indice, (nombre, peso) in enumerate(PESOS_RAPIDOS):
                fila, posicion = divmod(indice, 3)
                rejilla.columnconfigure(posicion, weight=1, uniform="pesos")
                control = boton(rejilla, f"{nombre}\n{peso} kg", lambda valor=peso: respuesta.set(valor),
                                "Referencia.Secundario")
                control.grid(row=fila, column=posicion, sticky="ew", padx=(0, ESPACIO[1]), pady=(0, ESPACIO[1]))
            return
        valores = opciones(self.datos, columna)
        etiquetas = etiquetas_opciones(valores)
        if len(valores) <= 6:
            for etiqueta, valor in etiquetas.items():
                ttk.Radiobutton(panel, text=etiqueta, variable=respuesta, value=valor).pack(fill="x")
        else:
            visible = tk.StringVar(panel, value=next((e for e, v in etiquetas.items() if v == respuesta.get()), ""))
            lista = ttk.Combobox(panel, textvariable=visible, values=list(etiquetas), state="readonly")
            lista.pack(fill="x")
            lista.bind("<<ComboboxSelected>>", lambda _: respuesta.set(etiquetas[visible.get()]))

    def validar_respuesta(self, columna):
        valor = self.respuestas[columna].get()
        if columna == PESO:
            return leer_peso(valor)
        if valor not in opciones(self.datos, columna):
            raise ErrorAnimal("Selecciona una opción disponible para continuar.")
        return valor

    def obtener_respuestas(self):
        return {columna: self.validar_respuesta(columna) for columna in CARACTERISTICAS}

    def siguiente(self):
        try:
            self.validar_respuesta(CARACTERISTICAS[self.paso])
            self.cambiar_paso(1)
        except ErrorAnimal as error:
            self.error_quiz.set(str(error))

    def cambiar_paso(self, avance):
        self.paso += avance
        self.ir("quiz")

    def reiniciar(self):
        for respuesta in self.respuestas.values():
            respuesta.set("")
        self.paso = 0
        self.resultado = None
        self.ir("quiz")

    def predecir(self):
        if self.modelo is None:
            self.error_quiz.set(self.error_modelo)
            return
        try:
            respuestas = self.obtener_respuestas()
            self.resultado = respuestas, self.servicio.predecir(self.modelo, respuestas)
            self.ir("resultado")
        except ErrorAnimal as error:
            self.error_quiz.set(str(error))

    def detalles(self, panel, respuestas):
        grupo = tk.Frame(panel, bg=COLOR["tarjeta"])
        grupo.pack(fill="x")
        grupo.columnconfigure(1, weight=1)
        for fila, (columna, valor) in enumerate(respuestas.items()):
            texto(grupo, ETIQUETAS[columna], color="suave").grid(
                row=fila, column=0, sticky="nw", padx=(0, ESPACIO[6]), pady=ESPACIO[1],
            )
            texto(grupo, formato_celda(columna, valor), ancho=320).grid(
                row=fila, column=1, sticky="nw", pady=ESPACIO[1],
            )

    def mostrar_resultado(self):
        respuestas, (animal, probabilidad, ranking) = self.resultado
        self.cabecera("Resultado de la predicción", "Las probabilidades son estimaciones del modelo.")
        principal = self.tarjeta()
        texto(principal, mostrar(animal), nivel="hero", color="acento", ancho=480).pack(anchor="w")
        texto(principal, f"{porcentaje(probabilidad)} de probabilidad estimada").pack(anchor="w")
        ttk.Progressbar(principal, maximum=1, value=probabilidad, takefocus=False).pack(fill="x", pady=ESPACIO[2])
        if probabilidad < UMBRAL_DUDA:
            texto(
                principal, "El modelo muestra poca seguridad en esta predicción. Revisa también las otras posibilidades.",
                color="aviso", ancho=490,
            ).pack(anchor="w", pady=ESPACIO[2])
        boton(principal, "Volver a intentarlo", self.reiniciar, "Primario").pack(anchor="w", pady=(ESPACIO[4], 0))
        alternativas = self.tarjeta()
        texto(alternativas, "Animales con mayor probabilidad", nivel="subtitulo").pack(anchor="w")
        for nombre, valor in ranking:
            fila = tk.Frame(alternativas, bg=COLOR["tarjeta"])
            fila.pack(fill="x", pady=(ESPACIO[2], 0))
            texto(fila, mostrar(nombre), ancho=320).pack(side="left")
            texto(fila, porcentaje(valor), color="acento").pack(side="right")
        panel = self.tarjeta()
        texto(panel, "Características ingresadas", nivel="subtitulo").pack(anchor="w", pady=(0, ESPACIO[2]))
        self.detalles(panel, respuestas)

    def registro(self):
        self.cabecera("Registrar animal", "Prepara varios ejemplos y guárdalos juntos en el dataset.")
        if self.datos is None:
            self.aviso_dataset()
            return
        panel = self.tarjeta()
        panel.columnconfigure((0, 1), weight=1, uniform="formulario")
        self.etiquetas_registro = {}
        self.listas_registro = {}
        for indice, columna in enumerate(COLUMNAS_TABLA):
            fila, posicion = divmod(indice, 2)
            grupo = tk.Frame(panel, bg=COLOR["tarjeta"])
            grupo.grid(row=fila, column=posicion, sticky="ew", padx=(0, ESPACIO[3] if posicion == 0 else 0),
                       pady=(0, ESPACIO[3]))
            texto(grupo, ETIQUETAS[columna], nivel="detalle", color="suave").pack(anchor="w", pady=(0, ESPACIO[1]))
            if columna == PESO:
                entrada = ttk.Entry(grupo, textvariable=self.campos[columna])
            else:
                entrada = ttk.Combobox(grupo, textvariable=self.campos[columna])
                self.listas_registro[columna] = entrada
            entrada.pack(fill="x")
        texto(
            panel, "Puedes elegir una categoría o escribir una nueva. Cambia solo los rasgos que varían entre ejemplos.",
            nivel="detalle", color="suave", ancho=500,
        ).grid(row=4, column=0, columnspan=2, sticky="w")
        acciones = tk.Frame(panel, bg=COLOR["tarjeta"])
        acciones.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(ESPACIO[3], 0))
        boton(acciones, "Agregar ejemplo", self.agregar_ejemplo, "Primario").pack(side="left")
        boton(acciones, "Limpiar formulario", self.limpiar_formulario).pack(side="left", padx=ESPACIO[2])
        self.mensaje_registro = texto(panel, ancho=500)
        self.mensaje_registro.grid(row=6, column=0, columnspan=2, sticky="w", pady=(ESPACIO[2], 0))

        lote = self.tarjeta()
        self.cantidad_pendientes = texto(lote, nivel="subtitulo")
        self.cantidad_pendientes.pack(anchor="w", pady=(0, ESPACIO[3]))
        contenedor, self.tabla_pendientes = self.tabla_animales(lote, altura=5)
        contenedor.pack(fill="x")
        acciones = tk.Frame(lote, bg=COLOR["tarjeta"])
        acciones.pack(fill="x", pady=(ESPACIO[4], 0))
        self.eliminar = boton(acciones, "Eliminar ejemplo seleccionado", self.eliminar_ejemplo)
        self.eliminar.pack(side="left")
        self.guardar = boton(acciones, "Guardar registros", self.guardar_ejemplos, "Primario")
        self.guardar.pack(side="right")
        self.tabla_pendientes.bind("<<TreeviewSelect>>", self.estado_eliminar)
        self.actualizar_pendientes()

    def actualizar_listas_registro(self):
        for columna, lista in self.listas_registro.items():
            disponibles = opciones(self.datos, columna) + [fila[columna] for fila in self.pendientes]
            etiquetas = etiquetas_opciones(dict.fromkeys(disponibles))
            self.etiquetas_registro[columna] = etiquetas
            lista.configure(values=list(etiquetas))

    def nota_registro(self, mensaje, color="acento"):
        self.mensaje_registro.configure(text=mensaje, fg=COLOR[color])

    def agregar_ejemplo(self):
        campos = {}
        for columna, variable in self.campos.items():
            ingresado = variable.get()
            campos[columna] = self.etiquetas_registro.get(columna, {}).get(ingresado, ingresado)
        if self.modelo is not None and campos[CLASE].strip():
            clases_registradas = self.datos[CLASE].unique()
            if clave(campos[CLASE]) not in {clave(nombre) for nombre in clases_registradas}:
                campos[CLASE] = valor_canonico(campos[CLASE], self.modelo.classes_)
        try:
            ejemplo = self.repositorio.preparar(campos, self.datos, self.pendientes)
            firma = self.repositorio.firma(ejemplo)
            existentes = self.datos.to_dict("records") + self.pendientes
            if any(self.repositorio.firma(fila) == firma for fila in existentes):
                raise ErrorAnimal("Ya existe un ejemplo con el mismo animal, peso y características.")
            self.pendientes.append(ejemplo)
            self.actualizar_pendientes()
            self.nota_registro("Ejemplo agregado a la lista. El formulario conserva los datos.")
        except ErrorAnimal as error:
            self.nota_registro(str(error), "error")

    def limpiar_formulario(self):
        for campo in self.campos.values():
            campo.set("")
        self.nota_registro("Formulario limpio.")

    def estado_eliminar(self, _evento=None):
        self.eliminar.state(["!disabled"] if self.tabla_pendientes.selection() else ["disabled"])

    def actualizar_pendientes(self):
        self.actualizar_listas_registro()
        self.llenar_animales(self.tabla_pendientes, self.pendientes)
        cantidad = len(self.pendientes)
        self.cantidad_pendientes.configure(text=f"Ejemplos pendientes ({cantidad})")
        self.guardar.state(["!disabled"] if cantidad else ["disabled"])
        self.estado_eliminar()

    def eliminar_ejemplo(self):
        seleccion = self.tabla_pendientes.selection()
        if seleccion:
            del self.pendientes[int(seleccion[0])]
            self.actualizar_pendientes()
            self.nota_registro("Ejemplo retirado de la lista.")

    def guardar_ejemplos(self):
        try:
            cantidad = len(self.pendientes)
            self.datos = self.repositorio.guardar(self.pendientes)
            self.pendientes.clear()
            self.ir("registro", arriba=False)
            mensaje = "Se guardó 1 registro." if cantidad == 1 else f"Se guardaron {cantidad} registros."
            self.nota_registro(mensaje)
            messagebox.showinfo("Registros guardados", mensaje, parent=self.raiz)
        except ErrorAnimal as error:
            self.nota_registro(str(error), "error")
            messagebox.showerror("Error al guardar registros", str(error), parent=self.raiz)

    @staticmethod
    def tabla_animales(panel, altura):
        return tabla(
            panel, COLUMNAS_TABLA, [ETIQUETAS[c] for c in COLUMNAS_TABLA],
            ANCHO_COLUMNAS, altura=altura, numericas=(PESO,),
        )

    @staticmethod
    def llenar_animales(arbol, registros):
        hijos = arbol.get_children()
        if hijos:
            arbol.delete(*hijos)
        for indice, registro in enumerate(registros):
            valores = [formato_celda(columna, registro[columna]) for columna in COLUMNAS_TABLA]
            arbol.insert("", "end", iid=str(indice), values=valores)

    def actualizar_dataset(self):
        self.cargar_dataset()
        self.ir(self.pagina)

    def dataset(self):
        self.cabecera("Dataset", "Consulta los registros y la distribución de ejemplos por animal.")
        if self.datos is None:
            self.aviso_dataset()
            return
        filtros = self.tarjeta()
        filtros.columnconfigure((0, 1, 2), weight=1)
        filtros_disponibles = [
            ("Buscar por nombre", None), ("Tipo de animal", CLASE), ("Alimentación", "alimentacion"),
        ]
        valores = []
        for indice, (etiqueta, columna) in enumerate(filtros_disponibles):
            grupo = tk.Frame(filtros, bg=COLOR["tarjeta"])
            grupo.grid(row=0, column=indice, sticky="ew", padx=(0, ESPACIO[2] if indice < 2 else 0))
            texto(grupo, etiqueta, nivel="detalle", color="suave").pack(anchor="w", pady=(0, ESPACIO[1]))
            variable = tk.StringVar(grupo)
            if columna:
                etiquetas = etiquetas_opciones(opciones(self.datos, columna))
                todos = "Todos los animales" if columna == CLASE else "Todas"
                while todos in etiquetas:
                    todos += " ·"
                variable.set(todos)
                campo = ttk.Combobox(grupo, values=[todos, *etiquetas], state="readonly", textvariable=variable, width=14)
            else:
                etiquetas = {}
                campo = ttk.Entry(grupo, textvariable=variable, width=16)
            campo.pack(fill="x")
            valores.append((variable, etiquetas))
        boton(filtros, "Actualizar tabla", self.actualizar_dataset).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(ESPACIO[3], 0),
        )

        panel = self.tarjeta()
        cantidad = texto(panel, nivel="subtitulo", ancho=500)
        cantidad.pack(anchor="w", pady=(0, ESPACIO[3]))
        contenedor, arbol = self.tabla_animales(panel, altura=8)
        contenedor.pack(fill="x")

        resumen = self.tarjeta()
        texto(resumen, "Registros por animal", nivel="subtitulo").pack(anchor="w", pady=(0, ESPACIO[3]))
        contenedor, conteos = tabla(resumen, ("animal", "cantidad"), ("Animal", "Registros"), (220, 120),
                                   altura=6, numericas=("cantidad",))
        contenedor.pack(fill="x")
        for nombre, total in self.datos[CLASE].value_counts(sort=False).sort_index().items():
            conteos.insert("", "end", values=(mostrar(nombre), total))

        def filtrar(*_):
            filtrados = self.datos
            busqueda = clave(valores[0][0].get())
            if busqueda:
                filtrados = filtrados[filtrados[CLASE].map(clave).str.contains(busqueda, regex=False)]
            for (_, columna), (variable, etiquetas) in zip(filtros_disponibles[1:], valores[1:]):
                seleccion = etiquetas.get(variable.get())
                if seleccion is not None:
                    filtrados = filtrados[filtrados[columna] == seleccion]
            cantidad.configure(text=f"{len(filtrados)} de {len(self.datos)} registros"
                                     if len(filtrados) else f"Sin coincidencias · {len(self.datos)} registros totales")
            self.llenar_animales(arbol, filtrados.to_dict("records"))

        for variable, _ in valores:
            variable.trace_add("write", filtrar)
        filtrar()

    def entrenamiento(self):
        self.cabecera("Reentrenar modelo", "Incorpora los registros actuales al clasificador y evalúalo con datos de prueba.")
        if self.datos is None and not self.entrenando:
            self.aviso_dataset()
            return
        panel = self.tarjeta()
        texto(panel, "Evaluación con división 75 / 25", nivel="subtitulo").pack(anchor="w")
        texto(
            panel, "El bosque aleatorio utiliza 200 árboles. Se recomiendan al menos ocho ejemplos por animal.",
            color="suave", ancho=500,
        ).pack(anchor="w", pady=(ESPACIO[2], ESPACIO[3]))
        if self.datos is not None:
            conteos = self.datos[CLASE].value_counts()
            escasos = [f"{mostrar(animal)} ({total})" for animal, total in conteos.items() if total < MINIMO_RECOMENDADO]
            if escasos:
                texto(
                    panel, "Animales por debajo de la recomendación: " + ", ".join(escasos) + ".",
                    color="aviso", ancho=500,
                ).pack(anchor="w", pady=(0, ESPACIO[3]))
            ausentes = self.clases_sin_ejemplos()
            if ausentes:
                texto(
                    panel, f"El modelo actual reconoce clases sin registros en el CSV: {ausentes}.",
                    color="aviso", ancho=500,
                ).pack(anchor="w", pady=(0, ESPACIO[3]))
        control = boton(panel, "Entrenar modelo", self.iniciar_entrenamiento, "Primario")
        control.pack(anchor="w")
        if self.entrenando:
            control.state(["disabled"])
            progreso = ttk.Progressbar(panel, mode="indeterminate", takefocus=False)
            progreso.pack(fill="x", pady=(ESPACIO[3], 0))
            progreso.start(14)
        if self.estado_entrenamiento:
            texto(
                panel, self.estado_entrenamiento, color=self.color_entrenamiento, ancho=500,
            ).pack(anchor="w", pady=(ESPACIO[3], 0))
        if self.informe:
            self.mostrar_informe(self.informe)

    def clases_sin_ejemplos(self):
        if self.modelo is None or self.datos is None:
            return ""
        ausentes = set(self.modelo.classes_) - set(self.datos[CLASE])
        return ", ".join(mostrar(animal) for animal in sorted(ausentes))

    def iniciar_entrenamiento(self):
        if self.entrenando:
            return
        try:
            self.datos = self.repositorio.leer()
            self.error_csv = ""
            division = self.servicio.dividir(self.datos)
        except ErrorAnimal as error:
            self.estado_entrenamiento = str(error)
            self.color_entrenamiento = "aviso"
            self.ir("entrenamiento", arriba=False)
            return
        mensaje = "Si el entrenamiento termina correctamente, se guardará el nuevo modelo."
        ausentes = self.clases_sin_ejemplos()
        if ausentes:
            mensaje += f"\n\nEl nuevo modelo dejará de reconocer estas clases sin ejemplos: {ausentes}."
        if not messagebox.askyesno("Reentrenar modelo", mensaje + "\n\n¿Continuar?", parent=self.raiz):
            return
        self.entrenando = True
        self.informe = None
        self.estado_entrenamiento = "Entrenando y evaluando el modelo…"
        self.color_entrenamiento = "suave"
        self.ir("entrenamiento", arriba=False)
        Thread(target=self.trabajo_entrenamiento, args=(division,), daemon=True).start()
        self.raiz.after(80, self.revisar_entrenamiento)

    def trabajo_entrenamiento(self, division):
        # El trabajador solo calcula, guarda y emite resultados. Tk se actualiza con after().
        try:
            modelo, informe = self.servicio.entrenar(division)
            self.cola_entrenamiento.put((modelo, informe, None))
        except ErrorAnimal as error:
            self.cola_entrenamiento.put((None, None, str(error)))
        except Exception:
            logging.exception("Error durante el reentrenamiento.")
            mensaje = "El entrenamiento falló. Revisa los datos e inténtalo de nuevo."
            self.cola_entrenamiento.put((None, None, mensaje))

    def revisar_entrenamiento(self):
        try:
            modelo, informe, error = self.cola_entrenamiento.get_nowait()
        except Empty:
            self.raiz.after(80, self.revisar_entrenamiento)
            return
        self.entrenando = False
        if error:
            self.estado_entrenamiento = error
            self.color_entrenamiento = "error"
        else:
            self.modelo, self.informe = modelo, informe
            self.error_modelo = ""
            self.estado_entrenamiento = "Modelo actualizado. Las nuevas predicciones ya lo utilizan."
            self.color_entrenamiento = "acento"
        if self.pagina in {"inicio", "entrenamiento"} or (self.pagina == "quiz" and self.paso == len(CARACTERISTICAS)):
            self.ir(self.pagina, arriba=False)
        if self.pagina != "entrenamiento":
            mostrar_mensaje = messagebox.showerror if error else messagebox.showinfo
            mostrar_mensaje("Reentrenamiento", self.estado_entrenamiento, parent=self.raiz)

    def mostrar_informe(self, informe):
        panel = self.tarjeta()
        texto(panel, "Resultados de evaluación", nivel="subtitulo").pack(anchor="w")
        texto(panel, porcentaje(informe.exactitud), nivel="cifra", color="acento").pack(
            anchor="w", pady=(ESPACIO[2], 0),
        )
        texto(panel, "Exactitud en los registros de prueba", color="suave").pack(anchor="w")
        texto(
            panel, f"{len(informe.clases)} clases · {informe.entrenamiento} de entrenamiento · {informe.prueba} de prueba",
            ancho=500,
        ).pack(anchor="w", pady=(ESPACIO[2], 0))

        reporte = self.tarjeta()
        texto(reporte, "Reporte de clasificación", nivel="subtitulo").pack(anchor="w", pady=(0, ESPACIO[3]))
        columnas = ("animal", "precision", "exhaustividad", "f1", "soporte")
        contenedor, arbol = tabla(reporte, columnas, ("Animal", "Precisión", "Exhaustividad", "F1", "Ejemplos"),
                                 (145, 95, 105, 85, 85), numericas=columnas[1:])
        contenedor.pack(fill="x")
        filas = [(str(indice), mostrar(clase)) for indice, clase in enumerate(informe.clases)]
        filas += [("macro avg", "Promedio macro"), ("weighted avg", "Promedio ponderado")]
        for clave_reporte, etiqueta in filas:
            metricas = informe.reporte[clave_reporte]
            valores = [porcentaje(metricas[k]) for k in ("precision", "recall", "f1-score")]
            arbol.insert("", "end", values=(etiqueta, *valores, int(metricas["support"])))

        matriz = self.tarjeta()
        texto(matriz, "Matriz de confusión", nivel="subtitulo").pack(anchor="w")
        texto(matriz, "Filas: animales registrados. Columnas: animales predichos.", color="suave", ancho=500).pack(
            anchor="w", pady=(ESPACIO[1], ESPACIO[3]),
        )
        columnas = ("real", *(f"clase_{indice}" for indice in range(len(informe.clases))))
        nombres = [mostrar(clase) for clase in informe.clases]
        contenedor, arbol = tabla(matriz, columnas, ["Animal real", *nombres],
                                 [135, *([105] * len(nombres))], numericas=columnas[1:])
        contenedor.pack(fill="x")
        for nombre, fila in zip(nombres, informe.matriz):
            arbol.insert("", "end", values=(nombre, *fila))

    def cerrar(self):
        if self.entrenando:
            messagebox.showinfo("Entrenamiento en curso", "Espera a que termine antes de cerrar Animal AI.", parent=self.raiz)
            return
        self.raiz.destroy()


def main():
    raiz = tk.Tk()
    AnimalAI(raiz, Path(__file__).resolve().parent)
    raiz.mainloop()


if __name__ == "__main__":
    main()
