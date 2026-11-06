# Amparo IA - Propuestas de Automatización Tecnológicas

Propuestas de Automatización Tecnológicas del proyecto de **Administración de Proyectos**

## Enlaces a las aplicaciones

1. Gestión de Riesgos: **[Abrir aplicación](https://gestionriesgosap.streamlit.app/)** | [`Riesgos/`](Riesgos/)

### Pasos para probar la aplicación de riesgos

1. Abra el enlace de la aplicación de gestion de riesgos. Si aparece un boton para "despertarla", presionelo y espere unos segundos.
2. Descargue la plantilla vacía desde la barra lateral y llenela con sus datos.
3. Suba el CSV en la barra lateral.
4. Explore las pestañas: matriz de calor, ranking, simulación y registro.
5. Cambie las iteraciones, la semilla o los filtros, y descargue la matriz en Excel desde la pestaña "Registro".

## Ejecución local

Requiere Python 3.10 o superior.

### Para la app de Riesgos:

Windows:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run Riesgos/appRiesgos.py
```

Nota: Si PowerShell bloquea la activación, ejecuta:
```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Riesgos/appRiesgos.py
```