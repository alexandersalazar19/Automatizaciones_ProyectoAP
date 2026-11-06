# Automatización de la gestión de riesgos - Amparo IA

Herramienta del Avance II que automatiza la matriz de riesgos del proyecto Amparo IA:
Calcula el puntaje y el nivel de cada riesgo, el valor monetario esperado, simula miles de escenarios
usando el algoritmo de Monte Carlo para estimar la reserva de contingencia y genera un dashboard y un Excel listo para el informe.

## Uso

### App
Ingrese al enlace de la aplicación de riesgos que se encuentra en el README global
o ejecutela en local con los pasos de **Ejecución local** del README global.

### Dashboard

1. Descargue la plantilla vacia desde la app y llenela con un riesgo por fila.
2. Suba el CSV en la barra lateral. La app no muestra datos hasta que se carga un archivo.
3. Ajuste el costo base, las iteraciones, la semilla y los filtros.
   El botón "Volver a simular" genera una nueva simulación con otra semilla.
4. Revise la matriz de calor, el ranking, la simulación y el registro.
   Descargue el CSV filtrado o la matriz completa en Excel.

## Formato del CSV

| Columna | Descripción |
|---|---|
| id | Identificador unico (R-01) |
| riesgo | Descripción breve |
| categoria | Tecnico, Legal, Recursos, Institucional, Calidad, Costos (texto libre) |
| causa | Origen del riesgo |
| probabilidad | 1 a 5 (1=10%, 2=30%, 3=50%, 4=70%, 5=90%) |
| impacto | 1 a 5 |
| costo_usd | Costo en USD si el riesgo ocurre |
| retraso_sprints | Retraso en sprints si el riesgo ocurre |
| estrategia | Evitar, Mitigar, Transferir o Aceptar |
| accion_respuesta | Acción concreta de respuesta |
| responsable | Persona a cargo del seguimiento |
| sprint_afectado | Sprint (1 a 13) en que impacta |
| estado | Abierto, Ocurrido, Mitigado o Cerrado |

## Método de cálculo

- **Puntaje** = probabilidad x impacto (1 a 25). Niveles: Crítico (16 o mas), Alto (10 a 15), Medio (5 a 9), Bajo (menos de 5).
- **Valor monetario esperado (VME)** = porcentaje de probabilidad x costo si ocurre.
- **Simulación Monte Carlo:** en cada escenario, cada riesgo activo ocurre o no segun su probabilidad.
  Los riesgos con estado Mitigado o Cerrado se excluyen y los Ocurridos se consideran seguros.
- **Percentiles (P50, P80, P90):** valor que ese porcentaje de los escenarios no supera.
- **Reserva de contingencia:** por defecto el P80 del costo simulado (configurable).
- **Retraso:** los retrasos de riesgos del mismo release se solapan, por lo que dentro de cada release
  se toma el mayor y luego se suman los releases (R1: sprints 1-5, R2: 6-7, R3: 8-11, R4: 12-13).

## Limitaciones

- La reserva cubre solo los riesgos identificados en el registro;
  los riesgos no previstos requieren una reserva de gestion aparte.
- La simulación trata los riesgos como independientes entre si.