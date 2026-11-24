# Predicción de Animales

Aplicación de escritorio (Tkinter) que clasifica animales con un modelo de
machine learning entrenado con scikit-learn.

## Requisitos

- Python 3.12
- Windows, macOS o Linux
- No necesita internet ni Google Colab para ejecutarse

## Instalación

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

> En Linux, si falla Tkinter, instala: `sudo apt install python3-tk`

## Estructura del proyecto

| Archivo | Descripción |
|---|---|
| `main.py` | Interfaz gráfica y punto de entrada |
| `servicios.py` | Carga del modelo, predicciones y reentrenamiento |
| `tema.py` | Colores y estilos de la interfaz |
| `modelo_animales.pkl` | Modelo entrenado |
| `dataset_animales_clasificacion.csv` | Datos para reentrenar |
| `requirements.txt` | Dependencias |

## Notas

- El modelo fue entrenado con **scikit-learn 1.6.1**. Usa esa versión
  (ya está fijada en `requirements.txt`) para evitar errores al cargar el `.pkl`.
- El modelo original reconoce 24 animales, pero el CSV solo tiene ejemplos de 22.
  La app avisa antes de reentrenar si el nuevo modelo dejaría de reconocer clases.
- Los archivos `.pkl` pueden ejecutar código al cargarse. Usa solo modelos de
  fuentes confiables.