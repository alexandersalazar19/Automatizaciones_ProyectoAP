import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from exportarCostos import exportarExcel
from motorCostos import (COLUMNAS_ADQUISICIONES,COLUMNAS_RECURSOS,GRUPOS,RELEASES,SPRINTS_TOTAL,
                         analisisFinanciero,cargarAdquisiciones,cargarRecursos,construirPresupuesto,
                         costoPorConcepto,costoPorRelease,reservaDesdeRiesgos)

st.set_page_config(page_title="Costos - Amparo IA",layout="wide")

COLORES_GRUPO={"Recursos humanos":"#4c78a8","Servicios externos":"#f58518","Tecnologia y licencias":"#54a24b",
               "Indirectos":"#b279a2","Contingencia":"#e45756"}

GUIA_RECURSOS=pd.DataFrame([
    ["recurso","Nombre de la persona o servicio","Ana Perez / Asesoria legal"],
    ["perfil","Perfil o rol del recurso","Desarrollador backend"],
    ["tipo","Planta (empleado del equipo), Contrato (empleado temporal) o Externo (servicio por horas)","Planta"],
    ["tarifa_hora_usd","Costo por hora en USD (numero)","24"],
    ["horas_sprint","Horas que trabaja en cada sprint (numero)","80"],
    ["sprints","Sprints en que trabaja: rango, lista o ambos (1 a 13)","1-13  |  8-11  |  2;5;6;8"]
],columns=["Columna","Descripcion","Ejemplo"])

GUIA_ADQUISICIONES=pd.DataFrame([
    ["concepto","Nombre del bien o servicio","NVIDIA DGX Spark"],
    ["categoria","Hardware, Licencias, Nube, Suscripciones o Servicios externos","Hardware"],
    ["costo_total_usd","Costo total en USD (numero); se reparte en partes iguales entre los sprints indicados","8000"],
    ["sprints","Sprints en que se paga: rango, lista o ambos (1 a 13)","7  |  1-13"]
],columns=["Columna","Descripcion","Ejemplo"])

def plantillaVacia(columnas:list)->bytes:
    return (",".join(columnas)+"\n").encode("utf-8")

def mostrarPantallaInicial():
    st.title("Costos y presupuesto - Amparo IA")
    st.info("Suba los dos archivos CSV (recursos humanos y adquisiciones) desde la barra lateral para comenzar.")
    st.write("Descargue las plantillas, llenelas con una fila por recurso o adquisicion y subalas en la barra lateral.")
    izq,der=st.columns(2)
    izq.download_button("Descargar plantilla de recursos",plantillaVacia(COLUMNAS_RECURSOS),"plantilla_recursos.csv","text/csv")
    der.download_button("Descargar plantilla de adquisiciones",plantillaVacia(COLUMNAS_ADQUISICIONES),"plantilla_adquisiciones.csv","text/csv")
    st.subheader("Como llenar los recursos")
    st.dataframe(GUIA_RECURSOS,hide_index=True)
    st.subheader("Como llenar las adquisiciones")
    st.dataframe(GUIA_ADQUISICIONES,hide_index=True)

#---------------- Barra lateral: datos ----------------
st.sidebar.header("Datos")
archivoRecursos=st.sidebar.file_uploader("Recursos humanos (CSV)",type="csv",key="recursos")
archivoAdquisiciones=st.sidebar.file_uploader("Adquisiciones (CSV)",type="csv",key="adquisiciones")
st.sidebar.download_button("Plantilla de recursos",plantillaVacia(COLUMNAS_RECURSOS),"plantilla_recursos.csv","text/csv")
st.sidebar.download_button("Plantilla de adquisiciones",plantillaVacia(COLUMNAS_ADQUISICIONES),"plantilla_adquisiciones.csv","text/csv")

if archivoRecursos is None or archivoAdquisiciones is None:
    mostrarPantallaInicial()
    st.stop()

try:
    recursos=cargarRecursos(archivoRecursos)
    adquisiciones=cargarAdquisiciones(archivoAdquisiciones)
except Exception as e:
    st.error(f"No se pudieron cargar los archivos: {e}")
    st.info("Revise que sigan el formato de las plantillas.")
    st.stop()

if recursos.empty and adquisiciones.empty:
    st.warning("Los archivos no contienen datos. Agregue al menos una fila.")
    st.stop()

#---------------- Barra lateral: parametros ----------------
st.sidebar.header("Parametros")
aplicarTarifas=st.sidebar.checkbox("Aplicar tarifas al personal de planta",value=True,
                                   help="Si se desmarca, el personal de planta no genera costo; el contrato y los servicios externos si.")
indirectosPct=st.sidebar.slider("Costos indirectos (% del costo directo)",0,20,8)/100

modoContingencia=st.sidebar.radio("Reserva de contingencia",["Porcentaje fijo","Desde la simulacion de riesgos"])
contingenciaModo="porcentaje"
contingenciaPct=0.15
contingenciaUsd=0.0
if modoContingencia=="Porcentaje fijo": contingenciaPct=st.sidebar.slider("Contingencia (% del costo base)",0,30,15)/100
else:
    archivoRiesgos=st.sidebar.file_uploader("Registro de riesgos (CSV)",type="csv",key="riesgos")
    percentilRiesgos=st.sidebar.selectbox("Percentil de la simulacion",["costo_p50","costo_p80","costo_p90"],index=1,
                                          format_func=lambda p:p.replace("costo_","").upper())
    if archivoRiesgos is None:
        st.title("Costos y presupuesto - Amparo IA")
        st.info("Suba el CSV del registro de riesgos en la barra lateral para calcular la reserva con la simulacion Monte Carlo, "
                "o vuelva al modo de porcentaje fijo.")
        st.stop()
    try:
        reserva=reservaDesdeRiesgos(archivoRiesgos,percentilRiesgos)
    except Exception as e:
        st.error(f"No se pudo calcular la reserva desde los riesgos: {e}")
        st.stop()
    contingenciaModo="riesgos"
    contingenciaUsd=reserva["reserva_usd"]
    st.sidebar.caption(f"Reserva calculada con {reserva['riesgosActivos']} riesgos activos: ${contingenciaUsd:,.0f}")

st.sidebar.header("Analisis financiero")
st.sidebar.caption("Supuestos que el equipo debe justificar en el informe.")
beneficioAnual=st.sidebar.number_input("Beneficio anual esperado (USD)",min_value=0.0,value=65000.0,step=1000.0)
costoOperacionAnual=st.sidebar.number_input("Costo de operacion anual (USD)",min_value=0.0,value=20000.0,step=1000.0)
tasaDescuento=st.sidebar.slider("Tasa de descuento anual (%)",0,30,10)/100
horizonteAnios=st.sidebar.select_slider("Horizonte de evaluacion (años)",options=list(range(1,11)),value=3)

#---------------- Calculos ----------------
p=construirPresupuesto(recursos,adquisiciones,aplicarTarifas,indirectosPct,contingenciaModo,contingenciaPct,contingenciaUsd)
tabla=p["tabla"]
detalle=p["detalle"]
fin=analisisFinanciero(p["presupuestoTotal"],beneficioAnual,costoOperacionAnual,tasaDescuento,horizonteAnios)

#---------------- Encabezado y KPIs ----------------
st.title("Costos y presupuesto - Amparo IA")
st.caption("Presupuesto por sprint, release y grupo de costo, con reserva de contingencia y analisis financiero basico.")

if not aplicarTarifas: st.info("Las tarifas del personal de planta estan desactivadas: su trabajo no genera costo en este presupuesto.")

c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Presupuesto total",f"${p['presupuestoTotal']:,.0f}")
c2.metric("Costo base",f"${p['costoBase']:,.0f}")
c3.metric("Reserva de contingencia",f"${p['contingencia']:,.0f}",f"{p['contingenciaPctBase']*100:.1f}% del costo base",delta_color="off")
c4.metric("Costo directo",f"${p['costoDirecto']:,.0f}")
c5.metric("Duracion",f"{SPRINTS_TOTAL*2} semanas",f"{SPRINTS_TOTAL} sprints",delta_color="off")

#---------------- Tabs ----------------
tabTiempo,tabComposicion,tabRelease,tabFinanciero,tabDetalle=st.tabs(
    ["Distribucion en el tiempo","Composicion","Por release","Analisis financiero","Detalle y exportacion"])

with tabTiempo:
    largo=tabla.reset_index().melt(id_vars="sprint",value_vars=GRUPOS,var_name="Grupo",value_name="USD")
    figBarras=px.bar(largo,x="sprint",y="USD",color="Grupo",color_discrete_map=COLORES_GRUPO,title="Costo por sprint")
    figBarras.update_layout(xaxis=dict(dtick=1,title="Sprint"),yaxis_title="USD")
    st.plotly_chart(figBarras)

    figS=go.Figure(go.Scatter(x=tabla.index,y=tabla["Acumulado"],mode="lines+markers",fill="tozeroy",name="Acumulado"))
    for release,(ini,fin_) in RELEASES.items():
        figS.add_vrect(x0=ini-0.5,x1=fin_+0.5,opacity=0.12,fillcolor="#7f7f7f" if release in ("R1","R3") else "#ffffff",
                       annotation_text=release,annotation_position="top left",line_width=0)
    figS.update_layout(title="Costo acumulado (curva S)",xaxis=dict(dtick=1,title="Sprint"),yaxis_title="USD")
    st.plotly_chart(figS)

    st.dataframe(tabla.round(0))

with tabComposicion:
    izq,der=st.columns(2)
    totales=p["totalesPorGrupo"].reset_index()
    totales.columns=["Grupo","USD"]
    figPastel=px.pie(totales,names="Grupo",values="USD",hole=0.4,color="Grupo",color_discrete_map=COLORES_GRUPO,
                     title="Presupuesto por grupo")
    izq.plotly_chart(figPastel)

    conceptos=costoPorConcepto(detalle)
    top=conceptos.head(10).sort_values("costo_usd")
    figTop=px.bar(top,x="costo_usd",y="concepto",orientation="h",color="grupo",color_discrete_map=COLORES_GRUPO,
                  title="Conceptos de mayor costo (sin indirectos ni contingencia)")
    figTop.update_layout(yaxis_title="",xaxis_title="USD")
    der.plotly_chart(figTop)

    st.dataframe(conceptos.round(2),hide_index=True)

with tabRelease:
    porRelease=costoPorRelease(tabla)
    figRelease=px.bar(porRelease,x="release",y="costo_usd",text=porRelease["porcentaje"].map(lambda x:f"{x*100:.1f}%"),
                      title="Costo por release (USD)")
    figRelease.update_layout(xaxis_title="Release",yaxis_title="USD")
    izq,der=st.columns([1,2])
    izq.dataframe(porRelease.assign(porcentaje=(porRelease["porcentaje"]*100).round(1)).round(0),hide_index=True)
    der.plotly_chart(figRelease)

with tabFinanciero:
    st.write("La inversion se realiza en el año 0 (26 semanas de proyecto) y los beneficios netos empiezan al lanzar la plataforma. "
             "Los valores de beneficio y operacion se ajustan en la barra lateral.")
    f1,f2,f3,f4=st.columns(4)
    f1.metric("VAN",f"${fin['van']:,.0f}")
    f2.metric("ROI",f"{fin['roi']*100:.1f}%")
    f3.metric("Relacion beneficio/costo",f"{fin['relacionBC']:.2f}")
    f4.metric("Recuperacion",f"{fin['paybackMeses']:.1f} meses" if fin["paybackMeses"] else "No se recupera")
    st.caption(f"Beneficio anual necesario para que el VAN sea 0: ${fin['beneficioEquilibrio']:,.0f}")

    anios=list(range(0,horizonteAnios+1))
    acumulado=[-p["presupuestoTotal"]+fin["beneficioNetoAnual"]*t for t in anios]
    figFlujo=go.Figure(go.Bar(x=anios,y=acumulado,marker_color=["#e45756" if v<0 else "#54a24b" for v in acumulado]))
    figFlujo.update_layout(title="Flujo de caja acumulado (sin descontar)",xaxis=dict(dtick=1,title="Año"),yaxis_title="USD")
    st.plotly_chart(figFlujo)

with tabDetalle:
    st.dataframe(detalle.round(2),hide_index=True)
    st.download_button("Descargar distribucion por sprint (CSV)",tabla.round(2).to_csv().encode("utf-8"),
                       "presupuesto_por_sprint.csv","text/csv")
    params={"aplicarTarifasPlanta":aplicarTarifas,"indirectosPct":indirectosPct,"contingenciaModo":contingenciaModo,
            "contingenciaPct":contingenciaPct,"contingenciaUsd":contingenciaUsd,"beneficioAnual":beneficioAnual,
            "costoOperacionAnual":costoOperacionAnual,"tasaDescuento":tasaDescuento,"horizonteAnios":horizonteAnios}
    st.download_button("Descargar presupuesto en Excel",exportarExcel(recursos,adquisiciones,params,p),"presupuesto_amparo_ia.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")