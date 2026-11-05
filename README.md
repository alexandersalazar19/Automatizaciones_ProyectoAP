# Amparo IA - Propuestas de Automatizacion Tecnologicas

Propuestas de Automatizacion Tecnologicas del proyecto de **Administracion de Proyectos**

### Pasos para probar la aplicacion de riesgos

1. Abra el enlace de la aplicacion de gestion de riesgos. Si aparece un boton para "despertarla", presionelo y espere unos segundos.
2. Descargue la plantilla vacia desde la barra lateral y llenela con sus datos.
3. Suba el CSV en la barra lateral.
4. Explore las pestanas: matriz de calor, ranking, simulacion y registro.
5. Cambie las iteraciones, la semilla o los filtros, y descargue la matriz en Excel desde la pestana "Registro".

## Enlaces a las aplicaciones

1. Gestion de Riesgos: **[Abrir aplicacion](ENLACE_RIESGOS)** | [`riesgos/`](riesgos/)

## Ejecucion local

Requiere Python 3.10 o superior.

Windows:
```bash
python3 -m venv .venv
source .venv\Scripts\activate
pip install -r requirements.txt
streamlit run riesgos/app.py
```

Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run riesgos/app.py
```