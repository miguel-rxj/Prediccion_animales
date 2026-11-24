"""Lectura, validación y persistencia de los archivos de Animal AI."""

from dataclasses import dataclass
from datetime import datetime
import logging
import math
from pathlib import Path
from shutil import copy2
from tempfile import NamedTemporaryFile
import unicodedata
import warnings

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PESO = "peso_kg"
CLASE = "animal"
CATEGORIAS = ["tiene_pelaje", "habitat", "alimentacion", "sonido", "tiene_patas"]
CARACTERISTICAS = [PESO, *CATEGORIAS]
COLUMNAS = [*CARACTERISTICAS, CLASE]
MINIMO_RECOMENDADO = 8
ETIQUETAS = {
    PESO: "Peso (kg)", "tiene_pelaje": "¿Tiene pelaje?", "habitat": "Hábitat",
    "alimentacion": "Alimentación", "sonido": "Sonido", "tiene_patas": "¿Tiene patas?",
    CLASE: "Animal",
}
ACENTOS = {
    "si": "sí", "leon": "león", "delfin": "delfín", "tiburon": "tiburón",
    "aguila": "águila", "pinguino": "pingüino", "pingüino": "pingüino",
    "carnivoro": "carnívoro", "herbivoro": "herbívoro", "omnivoro": "omnívoro",
    "maulla": "maúlla",
}


class ErrorAnimal(Exception):
    """Problema que se puede mostrar directamente en la interfaz."""


def clave(texto):
    """Normaliza diferencias de formato sin modificar los valores almacenados."""
    base = unicodedata.normalize("NFKD", str(texto).casefold())
    base = "".join(letra for letra in base if not unicodedata.combining(letra))
    return " ".join(base.replace("_", " ").split())


def mostrar(texto):
    forma = str(texto).replace("_", " ").strip()
    return ACENTOS.get(forma.casefold(), forma).capitalize()


def mostrar_peso(valor):
    return str(float(valor)).removesuffix(".0").replace(".", ",")


def leer_peso(texto):
    try:
        valor = float(str(texto).strip().replace(",", "."))
    except (ValueError, OverflowError) as error:
        raise ErrorAnimal("Ingresa un peso numérico en kilogramos, por ejemplo 0,00002.") from error
    if not math.isfinite(valor) or valor <= 0:
        raise ErrorAnimal("El peso debe ser un número finito mayor que cero.")
    return valor


def opciones(datos, columna):
    return sorted(datos[columna].unique(), key=lambda valor: (clave(valor), valor))


def valor_canonico(texto, existentes):
    if texto in existentes:
        return texto
    normalizado = clave(texto)
    for valor in existentes:
        if clave(valor) == normalizado:
            return valor
    return " ".join(texto.strip().lower().split())


def escribir_con_respaldo(ruta, escribir):
    """Prepara el archivo completo y lo sustituye solo tras crear el respaldo."""
    with NamedTemporaryFile(dir=ruta.parent, suffix=ruta.suffix, delete=False) as archivo:
        temporal = Path(archivo.name)
    try:
        escribir(temporal)
        if ruta.exists():
            sello = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            copy2(ruta, ruta.with_name(f"{ruta.stem}.{sello}.bak{ruta.suffix}"))
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)


class RepositorioDataset:
    def __init__(self, ruta):
        self.ruta = ruta

    def leer(self):
        try:
            datos = pd.read_csv(
                self.ruta, dtype={columna: str for columna in COLUMNAS if columna != PESO},
                keep_default_na=False, encoding="utf-8-sig", float_precision="round_trip",
            )
        except FileNotFoundError as error:
            raise ErrorAnimal(f"No se encontró {self.ruta.name}. Colócalo junto a main.py.") from error
        except (OSError, UnicodeError, ValueError) as error:
            logging.warning("Error al leer el CSV: %s", error)
            raise ErrorAnimal("No se pudo leer el CSV. Comprueba que sea legible y esté en formato UTF-8.") from error
        if len(datos.columns) != len(COLUMNAS) or set(datos.columns) != set(COLUMNAS):
            raise ErrorAnimal("El CSV debe contener exactamente las siete columnas del proyecto.")
        try:
            datos[PESO] = datos[PESO].map(leer_peso).astype(float)
        except ErrorAnimal as error:
            raise ErrorAnimal(f"Hay un peso inválido en el CSV. {error}") from error
        for columna in [*CATEGORIAS, CLASE]:
            if datos[columna].str.strip().eq("").any():
                raise ErrorAnimal(f"Hay valores vacíos en la columna {ETIQUETAS[columna]}.")
        return datos

    def preparar(self, campos, datos, pendientes):
        valores = {}
        for columna in [CLASE, *CARACTERISTICAS]:
            texto = str(campos[columna])
            if not texto.strip():
                raise ErrorAnimal(f"Completa el campo «{ETIQUETAS[columna]}».")
            if columna == PESO:
                valores[columna] = leer_peso(texto)
            else:
                existentes = list(datos[columna].unique()) + [fila[columna] for fila in pendientes]
                valores[columna] = valor_canonico(texto, existentes)
        return valores

    @staticmethod
    def firma(registro):
        return (registro[PESO], *(clave(registro[c]) for c in [*CATEGORIAS, CLASE]))

    def guardar(self, pendientes):
        if not pendientes:
            raise ErrorAnimal("Agrega al menos un ejemplo para guardar.")
        try:
            original = self.ruta.read_bytes()
            datos = self.leer()
            firmas = {self.firma(fila) for fila in datos.to_dict("records")}
            nuevos = []
            for pendiente in pendientes:
                fila = self.preparar(pendiente, datos, nuevos)
                firma = self.firma(fila)
                if firma in firmas:
                    raise ErrorAnimal(f"Ya existe un ejemplo idéntico de {mostrar(fila[CLASE])}.")
                nuevos.append(fila)
                firmas.add(firma)
            lote = pd.DataFrame(nuevos, columns=datos.columns)
            if self.ruta.read_bytes() != original:
                raise ErrorAnimal("El CSV cambió durante el guardado. Actualiza e inténtalo nuevamente.")
            # Agregar las filas al contenido original conserva sus valores y formato.
            salto = b"\r\n" if b"\r\n" in original else b"\n"
            separador = b"" if original.endswith((b"\r", b"\n")) else salto
            anexos = lote.to_csv(index=False, header=False, lineterminator=salto.decode()).encode("utf-8")
            escribir_con_respaldo(self.ruta, lambda temporal: temporal.write_bytes(original + separador + anexos))
            return pd.concat([datos, lote], ignore_index=True)
        except OSError as error:
            logging.warning("Error al guardar el CSV: %s", error)
            raise ErrorAnimal("No se pudieron guardar los registros. Comprueba los permisos y cierra el CSV si está abierto.") from error


@dataclass
class Informe:
    exactitud: float
    clases: list
    entrenamiento: int
    prueba: int
    reporte: dict
    matriz: list


class ServicioModelo:
    def __init__(self, ruta):
        self.ruta = ruta

    def cargar(self, datos=None):
        try:
            # El PKL es el artefacto local del proyecto. Se requiere su versión de sklearn.
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                modelo = joblib.load(self.ruta)
            if not isinstance(modelo, Pipeline):
                raise ValueError("Se esperaba un Pipeline entrenado.")
            columnas = set(modelo.feature_names_in_)
            if columnas != set(CARACTERISTICAS) or not len(modelo.classes_):
                raise ValueError("Las características o clases del modelo son incompatibles.")
            if datos is not None and not datos.empty:
                self.predecir(modelo, datos.iloc[0].to_dict())
            return modelo
        except FileNotFoundError as error:
            raise ErrorAnimal("No se encontró modelo_animales.pkl. Colócalo junto a main.py o reentrena el modelo.") from error
        except Exception as error:
            logging.warning("Error al cargar el modelo: %s", error)
            raise ErrorAnimal("No se pudo cargar el modelo. Instala las versiones de requirements.txt o reentrena el modelo.") from error

    @staticmethod
    def predecir(modelo, respuestas):
        entrada = pd.DataFrame([{columna: respuestas[columna] for columna in CARACTERISTICAS}])
        try:
            predicho = modelo.predict(entrada)[0]
            probabilidades = modelo.predict_proba(entrada)[0]
            ranking = sorted(zip(modelo.classes_, probabilidades), key=lambda par: -par[1])
            return predicho, dict(ranking)[predicho], ranking[:3]
        except Exception as error:
            logging.warning("Error al predecir: %s", error)
            raise ErrorAnimal("No se pudo obtener la predicción. Revisa el modelo y vuelve a intentarlo.") from error

    @staticmethod
    def dividir(datos):
        conteos = datos[CLASE].value_counts()
        insuficientes = conteos[conteos < 2]
        if len(conteos) < 2:
            animales = ", ".join(mostrar(animal) for animal in conteos.index)
            detalle = f" Clase disponible: {animales}." if animales else ""
            raise ErrorAnimal(f"Se necesitan al menos dos clases para entrenar.{detalle}")
        if not insuficientes.empty:
            faltantes = ", ".join(f"{mostrar(animal)} ({cantidad})" for animal, cantidad in insuficientes.items())
            raise ErrorAnimal(f"Cada clase requiere al menos 2 ejemplos para dividir los datos. Agrega ejemplos a {faltantes}. Se recomiendan 8 por animal.")
        try:
            division = train_test_split(
                datos[CARACTERISTICAS], datos[CLASE], test_size=0.25,
                random_state=42, stratify=datos[CLASE],
            )
        except ValueError as error:
            raise ErrorAnimal(
                "La división 75/25 necesita espacio para todas las clases en ambos grupos. "
                "Agrega más ejemplos, especialmente a los animales con menos registros."
            ) from error
        # Una división aceptada por sklearn puede omitir clases muy poco frecuentes.
        _, _, clases_entrenamiento, clases_prueba = division
        faltantes = set(conteos.index) - (set(clases_entrenamiento) & set(clases_prueba))
        if faltantes:
            animales = ", ".join(mostrar(animal) for animal in sorted(faltantes))
            raise ErrorAnimal(f"La división 75/25 dejó clases fuera de uno de los grupos. Agrega más ejemplos a {animales}.")
        return division

    def entrenar(self, division):
        x_ent, x_prueba, y_ent, y_prueba = division
        preprocesamiento = ColumnTransformer(
            [("categorias", OneHotEncoder(handle_unknown="ignore"), CATEGORIAS)],
            remainder="passthrough",
        )
        modelo = Pipeline([
            ("preprocesamiento", preprocesamiento),
            ("clasificador", RandomForestClassifier(n_estimators=200, random_state=42)),
        ])
        modelo.fit(x_ent, y_ent)
        predicciones = modelo.predict(x_prueba)
        clases = list(modelo.classes_)
        informe = Informe(
            accuracy_score(y_prueba, predicciones), clases, len(x_ent), len(x_prueba),
            # Las claves numéricas evitan colisiones entre nombres de animales y promedios.
            classification_report(
                y_prueba, predicciones, labels=clases, target_names=[str(i) for i in range(len(clases))],
                output_dict=True, zero_division=0,
            ),
            confusion_matrix(y_prueba, predicciones, labels=clases).tolist(),
        )
        try:
            escribir_con_respaldo(self.ruta, lambda temporal: joblib.dump(modelo, temporal))
        except OSError as error:
            logging.warning("Error al guardar el modelo: %s", error)
            raise ErrorAnimal("El entrenamiento terminó, pero no se pudo guardar el modelo. Comprueba los permisos de la carpeta.") from error
        return modelo, informe
