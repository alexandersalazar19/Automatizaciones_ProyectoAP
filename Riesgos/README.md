# Automatizacion de la gestion de riesgos - Amparo IA

Herramienta del Avance II que automatiza la matriz de riesgos del proyecto Amparo IA:
Calcula el puntaje y el nivel de cada riesgo, el valor monetario esperado, simula miles de escenarios
usando el algoritmo de Monte Carlo para estimar la reserva de contingencia y genera un dashboard y un Excel listo para el informe.

## Contenido

| Archivo | Funcion |
|---|---|
| `motor.py` | Calculos: puntaje, nivel, valor monetario esperado, matriz de calor y simulacion Monte Carlo |
| `app.py` | Dashboard en Streamlit (carga del CSV, filtros, graficos, simulacion y descargas) |
| `exportar.py` | Genera el Excel con la matriz de riesgos (tambien se puede usar por linea de comandos) |
| `riesgos.csv` | Registro de riesgos de ejemplo del proyecto |
| `plantilla_riesgos.csv` | Plantilla vacia con las columnas requeridas |
| `requirements.txt` | Dependencias de Python |

## Instalacion

Requiere Python 3.10 o superior.

Windows:
```bash
python3 -m venv .venv
source .venv\Scripts\activate
pip install -r requirements.txt
```

Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Dashboard

```bash
streamlit run app.py
```

1. Descargue la plantilla vacia desde la app y llenela con un riesgo por fila.
2. Suba el CSV en la barra lateral. La app no muestra datos hasta que se carga un archivo.
3. Ajuste el costo base, las iteraciones, la semilla y los filtros.
   El boton "Volver a simular" genera una nueva simulacon con otra semilla.
4. Revise la matriz de calor, el ranking, la simulacion y el registro.
   Descargue el CSV filtrado o la matriz completa en Excel.

### Linea de comandos

```bash
python motor.py riesgos.csv 120000                    # resumen en consola (el 2do dato es el costo base)
python exportar.py riesgos.csv matriz_riesgos.xlsx 120000   # genera el Excel
```

## Formato del CSV

| Columna | Descripcion |
|---|---|
| id | Identificador unico (R-01) |
| riesgo | Descripcion breve |
| categoria | Tecnico, Legal, Recursos, Institucional, Calidad, Costos (texto libre) |
| causa | Origen del riesgo |
| probabilidad | 1 a 5 (1=10%, 2=30%, 3=50%, 4=70%, 5=90%) |
| impacto | 1 a 5 |
| costo_usd | Costo en USD si el riesgo ocurre |
| retraso_sprints | Retraso en sprints si el riesgo ocurre |
| estrategia | Evitar, Mitigar, Transferir o Aceptar |
| accion_respuesta | Accion concreta de respuesta |
| responsable | Persona a cargo del seguimiento |
| sprint_afectado | Sprint (1 a 13) en que impacta |
| estado | Abierto, Ocurrido, Mitigado o Cerrado |

## Metodo de calculo

- **Puntaje** = probabilidad x impacto (1 a 25). Niveles: Critico (16 o mas), Alto (10 a 15), Medio (5 a 9), Bajo (menos de 5).
- **Valor monetario esperado (VME)** = porcentaje de probabilidad x costo si ocurre.
- **Simulacion Monte Carlo:** en cada escenario, cada riesgo activo ocurre o no segun su probabilidad.
  Los riesgos con estado Mitigado o Cerrado se excluyen y los Ocurridos se consideran seguros.
- **Percentiles (P50, P80, P90):** valor que ese porcentaje de los escenarios no supera.
- **Reserva de contingencia:** por defecto el P80 del costo simulado (configurable).
- **Retraso:** los retrasos de riesgos del mismo release se solapan, por lo que dentro de cada release
  se toma el mayor y luego se suman los releases (R1: sprints 1-5, R2: 6-7, R3: 8-11, R4: 12-13).

## Limitaciones

- La reserva cubre solo los riesgos identificados en el registro;
  los riesgos no previstos requieren una reserva de gestion aparte.
- La simulacion trata los riesgos como independientes entre si.