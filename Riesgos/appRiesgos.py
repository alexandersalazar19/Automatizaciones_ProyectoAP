import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from exportarRiesgos import exportarExcel
from motorRiesgos import COLUMNAS,cargarRiesgos,simular,contingencia,resumenPorNivel,riesgosActivos

st.set_page_config(page_title="Riesgos - Amparo IA",layout="wide")

COLORES_NIVEL={"Critico":"#d62728","Alto":"#ff7f0e","Medio":"#f2c200","Bajo":"#2ca02c"}
COLUMNAS_TABLA=["id","riesgo","categoria","probabilidad","impacto","puntaje","nivel","vme_usd",
                "retraso_sprints","estrategia","accion_respuesta","responsable","sprint_afectado","estado"]

@st.cache_data
def simularCache(df:pd.DataFrame,iteraciones:int,semilla:int)->dict:
    return simular(df,iteraciones,semilla)

GUIA_COLUMNAS=pd.DataFrame([
    ["id","Identificador unico del riesgo","R-01"],
    ["riesgo","Descripcion breve del riesgo","Dataset insuficiente para el ajuste fino"],
    ["categoria","Tipo de riesgo (texto libre)","Tecnico, Legal, Recursos, Institucional, Calidad, Costos"],
    ["causa","Origen o causa del riesgo","Pocos ejemplos bien estructurados"],
    ["probabilidad","Escala de 1 a 5 (1=10%, 2=30%, 3=50%, 4=70%, 5=90%)","4"],
    ["impacto","Escala de 1 a 5 (1=muy bajo, 5=muy alto)","5"],
    ["costo_usd","Costo en USD si el riesgo ocurre (numero)","2500"],
    ["retraso_sprints","Retraso en sprints si el riesgo ocurre (numero)","2"],
    ["estrategia","Respuesta al riesgo","Evitar, Mitigar, Transferir, Aceptar"],
    ["accion_respuesta","Que se hara concretamente","Contratar anotacion adicional"],
    ["responsable","Persona a cargo del seguimiento","Nombre del integrante"],
    ["sprint_afectado","Sprint en que impacta (numero entero, 1 a 13)","8"],
    ["estado","Estado actual del riesgo","Abierto, Ocurrido, Mitigado, Cerrado"]
],columns=["Columna","Descripcion","Valores o ejemplo"])

def plantillaVacia()->bytes:
    return (",".join(COLUMNAS)+"\n").encode("utf-8")

def mostrarPantallaInicial():
    st.title("Gestion de riesgos - Amparo IA")
    st.info("Suba un archivo CSV con el registro de riesgos desde la barra lateral para comenzar.")
    st.subheader("Plantilla")
    st.write("Descargue la plantilla, llenela con un riesgo por fila (deje los nombres de las columnas tal como estan) "
             "y subala en la barra lateral.")
    st.download_button("Descargar plantilla vacia (CSV)",plantillaVacia(),"plantilla_riesgos.csv","text/csv")
    st.subheader("Como llenarla")
    st.dataframe(GUIA_COLUMNAS,hide_index=True)
    st.caption("Los riesgos con estado Mitigado o Cerrado no se incluyen en la simulacion.")

def nuevaSemilla():
    st.session_state["semilla"]=random.randint(1,999999)

def construirMapaCalor(df:pd.DataFrame)->go.Figure:
    #Cada celda muestra los ID de los riesgos con esa probabilidad e impacto
    probabilidades=list(range(5,0,-1))
    impactos=list(range(1,6))
    z=[[p*i for i in impactos] for p in probabilidades]
    texto=[["<br>".join(df[(df["probabilidad"]==p)&(df["impacto"]==i)]["id"]) for i in impactos] for p in probabilidades]

    #Colores por escalones segun los niveles de nivelPrioridad (zmin=1, zmax=25)
    escala=[[0,"#2ca02c"],[0.146,"#2ca02c"],[0.146,"#f2c200"],[0.354,"#f2c200"],
            [0.354,"#ff7f0e"],[0.604,"#ff7f0e"],[0.604,"#d62728"],[1,"#d62728"]]

    fig=go.Figure(go.Heatmap(z=z,x=impactos,y=probabilidades,text=texto,texttemplate="%{text}",
                             colorscale=escala,zmin=1,zmax=25,showscale=False,xgap=3,ygap=3,
                             hovertemplate="Probabilidad %{y} x Impacto %{x}<extra></extra>"))
    fig.update_layout(xaxis_title="Impacto",yaxis_title="Probabilidad",height=520,xaxis=dict(dtick=1),yaxis=dict(dtick=1))
    return fig

def construirHistograma(valores,titulo:str,etiquetaX:str,percentiles:dict,formato:str)->go.Figure:
    fig=px.histogram(x=valores,nbins=40,title=titulo,labels={"x":etiquetaX})
    fig.update_traces(marker_color="#4c78a8")
    colores={"P50":"#2ca02c","P80":"#ff7f0e","P90":"#d62728"}
    for nombre,valor in percentiles.items():
        fig.add_vline(x=valor,line_dash="dash",line_color=colores[nombre],annotation_text=f"{nombre}: {valor:{formato}}",annotation_position="top")
    fig.update_layout(yaxis_title="Escenarios",showlegend=False)
    return fig


#---------------- Barra lateral ----------------
st.sidebar.header("Configuracion")
archivo=st.sidebar.file_uploader("Registro de riesgos (CSV)",type="csv")
st.sidebar.download_button("Descargar plantilla vacia",plantillaVacia(),"plantilla_riesgos.csv","text/csv")
if archivo is None:
    mostrarPantallaInicial()
    st.stop()
costoBase=st.sidebar.number_input("Costo base del proyecto (USD)",min_value=0.0,value=120000.0,step=1000.0)
iteraciones=st.sidebar.select_slider("Iteraciones de la simulacion",options=[5000,10000,50000,100000,500000,1000000],
                                     value=10000,format_func=lambda n:f"{n:,}")
if "semilla" not in st.session_state: st.session_state["semilla"]=42
st.sidebar.number_input("Semilla aleatoria",min_value=0,step=1,key="semilla",
                        help="Misma semilla = mismos resultados. Cambiela o use el boton para obtener otra corrida.")
st.sidebar.button("Volver a simular (nueva semilla)",on_click=nuevaSemilla)
soloFiltrados=st.sidebar.checkbox("Simular solo los riesgos filtrados",value=False)
percentil=st.sidebar.selectbox("Percentil para la contingencia",["costo_p50","costo_p80","costo_p90"],
                               index=1,format_func=lambda p:p.replace("costo_","").upper())

try:
    df=cargarRiesgos(archivo)
except Exception as e:
    st.error(f"No se pudo cargar el CSV: {e}")
    st.info("Revise que el archivo siga el formato de la plantilla.")
    st.stop()

if df.empty:
    st.warning("El CSV no contiene riesgos. Agregue al menos una fila con la informacion de un riesgo.")
    st.stop()

st.sidebar.header("Filtros")
niveles=st.sidebar.multiselect("Nivel",list(COLORES_NIVEL),default=list(COLORES_NIVEL))
categorias=st.sidebar.multiselect("Categoria",sorted(df["categoria"].unique()),default=sorted(df["categoria"].unique()))
responsables=st.sidebar.multiselect("Responsable",sorted(df["responsable"].unique()),default=sorted(df["responsable"].unique()))
estados=st.sidebar.multiselect("Estado",sorted(df["estado"].unique()),default=sorted(df["estado"].unique()))

dfFiltrado=df[df["nivel"].isin(niveles)&df["categoria"].isin(categorias)&
              df["responsable"].isin(responsables)&df["estado"].isin(estados)]

#---------------- Calculos ----------------
dfSim=dfFiltrado if soloFiltrados else df
sim=simularCache(dfSim,iteraciones,st.session_state["semilla"])
cont=contingencia(sim,costoBase,percentil)
porNivel=resumenPorNivel(riesgosActivos(df))

#---------------- Encabezado y KPIs ----------------
st.title("Gestion de riesgos - Amparo IA")
st.caption("Matriz de riesgos automatizada: puntaje, valor monetario esperado y simulacion Monte Carlo. "
           "Los filtros afectan la matriz, el ranking y la tabla; la simulacion usa todos los riesgos activos, "
           "salvo que marque la opcion de simular solo los filtrados.")

c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Riesgos activos",len(riesgosActivos(df)))
c2.metric("Criticos",int(porNivel["Critico"]))
c3.metric("Altos",int(porNivel["Alto"]))
c4.metric("VME total",f"${df['vme_usd'].sum():,.0f}")
c5.metric(f"Contingencia {percentil.replace('costo_','').upper()}",f"${cont['reserva_usd']:,.0f}",
          f"{cont['reserva_pct']}% del costo base" if "reserva_pct" in cont else None,delta_color="off")

criticos=df[df["nivel"]=="Critico"]
if not criticos.empty:
    with st.container(border=True):
        st.error(f"Alerta: {len(criticos)} riesgo(s) critico(s) requieren seguimiento prioritario")
        for _,r in criticos.iterrows():
            st.write(f"**{r['id']}** - {r['riesgo']} (puntaje {r['puntaje']}, sprint {r['sprint_afectado']}, "
                     f"responsable: {r['responsable']})")

#---------------- Tabs ----------------
tabMapa,tabRanking,tabSim,tabRegistro=st.tabs(["Matriz de calor","Ranking","Simulacion","Registro"])

with tabMapa:
    st.plotly_chart(construirMapaCalor(dfFiltrado))

with tabRanking:
    izq,der=st.columns(2)
    figPuntaje=px.bar(dfFiltrado.sort_values("puntaje"),x="puntaje",y="id",orientation="h",color="nivel",
                      color_discrete_map=COLORES_NIVEL,hover_data=["riesgo","vme_usd","responsable"],
                      title="Riesgos por puntaje (probabilidad x impacto)")
    figPuntaje.update_layout(yaxis={"categoryorder":"total ascending"},yaxis_title="")
    izq.plotly_chart(figPuntaje)

    vmePorCategoria=dfFiltrado.groupby("categoria",as_index=False)["vme_usd"].sum().sort_values("vme_usd")
    figVme=px.bar(vmePorCategoria,x="vme_usd",y="categoria",orientation="h",
                  title="Valor monetario esperado por categoria (USD)")
    figVme.update_layout(yaxis_title="",xaxis_title="VME (USD)")
    der.plotly_chart(figVme)

with tabSim:
    st.write(f"Se simularon **{sim['iteraciones']:,}** escenarios (semilla {st.session_state['semilla']}). En cada uno, cada riesgo activo "
             "ocurre o no segun su probabilidad. Un percentil Pxx indica el valor que el xx % de los escenarios no supera.")
    percCosto={"P50":sim["costo_p50"],"P80":sim["costo_p80"],"P90":sim["costo_p90"]}
    percRetraso={"P50":sim["retraso_p50"],"P80":sim["retraso_p80"],"P90":sim["retraso_p90"]}

    izq,der=st.columns(2)
    izq.plotly_chart(construirHistograma(sim["costos_simulados"],"Costo acumulado de los riesgos","Costo (USD)",percCosto,",.0f"))
    der.plotly_chart(construirHistograma(sim["retrasos_simulados"],"Retraso acumulado (sprints)","Retraso (sprints)",percRetraso,".0f"))

    tablaPerc=pd.DataFrame({"Percentil":["Media","P50","P80","P90"],
                            "Costo (USD)":[sim["costo_medio"],sim["costo_p50"],sim["costo_p80"],sim["costo_p90"]],
                            "Retraso (sprints)":[sim["retraso_medio"],sim["retraso_p50"],sim["retraso_p80"],sim["retraso_p90"]]})
    st.dataframe(tablaPerc.round(1),hide_index=True)

with tabRegistro:
    st.dataframe(dfFiltrado[COLUMNAS_TABLA],hide_index=True)
    st.download_button("Descargar registro filtrado (CSV)",dfFiltrado[COLUMNAS_TABLA].to_csv(index=False).encode("utf-8"),
                       "riesgos_filtrados.csv","text/csv")
    if not dfSim.empty:
        st.download_button("Descargar matriz de riesgos en Excel",
                           exportarExcel(dfSim,sim,cont,costoBase,st.session_state["semilla"],percentil),
                           "matriz_riesgos.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")