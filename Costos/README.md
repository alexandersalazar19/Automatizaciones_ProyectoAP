# Automatización de costos y presupuesto - Amparo IA

Herramienta del Avance II que automatiza el Plan de Gestión de Costos y el Presupuesto del proyecto Amparo IA.
A partir del equipo, las horas por sprint y las adquisiciones, calcula el presupuesto por sprint y por release,
la reserva de contingencia (porcentaje fijo o tomada de la simulación Monte Carlo de la automatización de riesgos),
el análisis financiero básico, y genera un dashboard y un Excel con fórmulas listo para el informe.

## Uso

1. Abra la aplicación (enlace en el README global) o ejecútela en local: `streamlit run Costos/appCostos.py`.
2. Suba `recursos.csv` y `adquisiciones.csv` en la barra lateral. Las plantillas vacías se descargan desde la propia app.
3. Ajuste los parámetros: tarifas del personal de planta (sí/no), costos indirectos, reserva de contingencia y supuestos financieros.
4. Para calcular la reserva con la simulación de riesgos, elija "Desde la simulación de riesgos" y suba el CSV de riesgos.
   Requiere que la carpeta `Riesgos` esté junto a `Costos`, como en este repositorio.
5. Revise las pestañas y descargue el presupuesto en Excel desde "Detalle y exportación".

También se puede generar la salida por consola con `python motorCostos.py`.

## Formato de los CSV

### recursos.csv

| Columna | Descripción |
|---|---|
| recurso | Nombre de la persona o servicio |
| perfil | Perfil o rol |
| tipo | `Planta`, `Contrato` o `Externo` |
| tarifa_hora_usd | Costo por hora en USD |
| horas_sprint | Horas trabajadas en cada sprint |
| sprints | Sprints en que trabaja: rango (`1-13`), lista (`2;5;6;8`) o ambos (`1-3;7`) |

### adquisiciones.csv

| Columna | Descripción |
|---|---|
| concepto | Bien o servicio |
| categoria | Hardware, Licencias, Nube, Suscripciones o Servicios externos |
| costo_total_usd | Costo total en USD; se reparte en partes iguales entre los sprints indicados |
| sprints | Sprints en que se paga (mismo formato que arriba) |

## Método de cálculo

- **Recursos humanos y servicios externos** = tarifa por hora x horas por sprint, en cada sprint indicado.
  Si el interruptor de tarifas está apagado, el personal de planta no genera costo.
- **Tecnología y licencias**: costo total de cada adquisición repartido entre sus sprints.
- **Costos indirectos** = porcentaje del costo directo de cada sprint (8 % por defecto).
- **Costo base** = costo directo + indirectos.
- **Reserva de contingencia**: porcentaje del costo base (15 % por defecto) o el monto de la simulación de riesgos
  (P50, P80 o P90). Se distribuye por sprint en proporción al costo base.
- **Presupuesto total** = costo base + reserva de contingencia.
- **Costo por release** con la agrupación del plan: R1 (sprints 1-5), R2 (6-7), R3 (8-11) y R4 (12-13).
- **Análisis financiero**: la inversión se realiza en el año 0 y los beneficios netos anuales empiezan al lanzar la plataforma.
  Se calculan VAN, ROI, relación beneficio/costo, recuperación en meses y el beneficio anual necesario para VAN = 0.

## Excel exportado

| Hoja | Contenido |
|---|---|
| Resumen | Parámetros editables (azul), presupuesto total y análisis financiero con fórmulas |
| Distribucion | Costo por sprint y grupo, acumulado, y gráficos de barras apiladas y curva S |
| Por release | Costo y porcentaje de cada release |
| Por concepto | Horas y costo por recurso o adquisición |
| Detalle | Una fila por concepto y sprint; tarifas y horas editables |

Los parámetros del Resumen y las tarifas del Detalle son editables y todo el libro se recalcula, incluido el interruptor
de tarifas del personal de planta y el modo de la reserva de contingencia.

## Limitaciones

- Los costos indirectos, el beneficio anual y el costo de operación son supuestos del equipo;
  el análisis financiero depende por completo de ellos.
- La reserva de contingencia cubre solo los riesgos identificados; los riesgos no previstos requieren una reserva de gestión aparte.
- El costo de cada adquisición se reparte en partes iguales entre sus sprints, sin considerar fechas de pago exactas.