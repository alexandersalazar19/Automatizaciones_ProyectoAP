import sys
from pathlib import Path
import numpy as np
import pandas as pd

COLUMNAS=["id", "riesgo", "categoria", "causa", "probabilidad", "impacto", "costo_usd", "retraso_sprints",
          "estrategia", "accion_respuesta", "responsable", "sprint_afectado", "estado"]

#Escalas de 1-5 a porcentajes
PROB_PORCENTAJE={1: 0.10,
                2: 0.30,
                3: 0.50,
                4: 0.70,
                5: 0.90}

ESTADOS_INACTIVOS={"cerrado","mitigado"} #se excluyen de la simulacion

def numRelease(sprint:int)->str:
    if sprint<=5: return "R1"
    if sprint<=7: return "R2"
    if sprint<=11: return "R3"
    return "R4"

def nivelPrioridad(puntaje:int)->str:
    if puntaje>=16: return "Critico"
    if puntaje>=10: return "Alto"
    if puntaje>=5: return "Medio"
    return "Bajo"

def cargarRiesgos(ruta:str | Path="riesgos.csv")->pd.DataFrame:
    df=pd.read_csv(ruta)

    faltantes=[c for c in COLUMNAS if c not in df.columns]
    if faltantes: raise ValueError(f"Faltan columnas en el CSV: {faltantes}")

    for col in ("probabilidad","impacto"):
        if not df[col].between(1,5).all(): raise ValueError(f"'{col}' debe estar entre 1 y 5")

    df["puntaje"]=df["probabilidad"]*df["impacto"]
    df["nivel"]=df["puntaje"].apply(nivelPrioridad)
    df["prob_pct"]=df["probabilidad"].map(PROB_PORCENTAJE)
    df["vme_usd"]=(df["prob_pct"]*df["costo_usd"]).round(2)  #valor monetario esperado
    df["vme_sprints"]=(df["prob_pct"]*df["retraso_sprints"]).round(2)

    return df.sort_values("puntaje",ascending=False).reset_index(drop=True)

def riesgosActivos(df:pd.DataFrame)->pd.DataFrame:
    return df[~df["estado"].str.lower().isin(ESTADOS_INACTIVOS)]

def simular(df:pd.DataFrame,iteraciones:int=10000,semilla:int=42)->dict:
    #Monte Carlo: en cada iteracion cada riesgo activo ocurre con su probabilidad
    #Devuelve la distribucion de costo y retraso acumulados
    activos=riesgosActivos(df)
    rng=np.random.default_rng(semilla)

    probs=activos["prob_pct"].to_numpy()
    #Un riesgo ya ocurrido se considera seguro
    probs=np.where(activos["estado"].str.lower()=="ocurrido",1.0,probs)
    costos=activos["costo_usd"].to_numpy()
    retrasos=activos["retraso_sprints"].to_numpy()

    ocurre=rng.random((iteraciones,len(activos)))<probs
    costo_total=ocurre @ costos

    #Los retrasos de riesgos del mismo release se solapan (el trabajo corre en paralelo y los sprints absorben parte del atraso),
    #por lo que dentro de cada release se toma el mayor retraso y luego se suman los releases.
    releases=activos["sprint_afectado"].astype(int).map(numRelease).to_numpy()
    retraso_total=np.zeros(iteraciones)
    for rel in np.unique(releases):
        cols=np.where(releases==rel)[0]
        retraso_total+=(ocurre[:,cols]*retrasos[cols]).max(axis=1)

    def pct(arr,p):
        return float(np.percentile(arr, p))

    return{
        "iteraciones": iteraciones,
        "costo_medio": float(costo_total.mean()),
        "costo_p50": pct(costo_total,50),
        "costo_p80": pct(costo_total,80),
        "costo_p90": pct(costo_total,90),
        "retraso_medio": float(retraso_total.mean()),
        "retraso_p50": pct(retraso_total,50),
        "retraso_p80": pct(retraso_total,80),
        "retraso_p90": pct(retraso_total,90),
        "costos_simulados": costo_total,
        "retrasos_simulados": retraso_total
    }

def contingencia(sim:dict,costoBase:float | None=None,percentil:str="costo_p80")->dict:
    #Reserva de contingencia recomendada (por defecto P80 del costo simulado)
    reserva=sim[percentil]
    resultado={"reserva_usd":round(reserva,2),"criterio":percentil.upper()}
    if costoBase: resultado["reserva_pct"]=round(reserva/costoBase*100,2)
    return resultado

def resumenPorNivel(df:pd.DataFrame)->pd.Series:
    orden=["Critico","Alto","Medio","Bajo"]
    return df["nivel"].value_counts().reindex(orden,fill_value=0)

def matrizCalor(df:pd.DataFrame)->pd.DataFrame:
    tabla=pd.crosstab(df["probabilidad"],df["impacto"])
    return tabla.reindex(index=range(5,0,-1),columns=range(1,6),fill_value=0)

if __name__=="__main__":
    ruta=sys.argv[1] if len(sys.argv)>1 else Path(__file__).with_name("riesgos.csv")
    base=float(sys.argv[2]) if len(sys.argv)>2 else None

    datos=cargarRiesgos(ruta)
    sim=simular(datos)
    cont=contingencia(sim,base)

    print(f"\n=== Registro de riesgos: {len(datos)} riesgos ===")
    print(datos[["id", "riesgo", "puntaje", "nivel", "vme_usd", "responsable"]].to_string(index=False))

    print("\n=== Riesgos por nivel ===")
    print(resumenPorNivel(datos).to_string())

    print("\n=== Matriz de calor (filas: probabilidad, columnas: impacto) ===")
    print(matrizCalor(datos).to_string())

    print(f"\n=== Simulacion Monte Carlo con {sim['iteraciones']:,} iteraciones ===")
    print(f"Costo de riesgos  -> medio: ${sim['costo_medio']:,.0f} | P50: ${sim['costo_p50']:,.0f} "
          f"| P80: ${sim['costo_p80']:,.0f} | P90: ${sim['costo_p90']:,.0f}")
    print(f"Retraso (sprints) -> medio: {sim['retraso_medio']:.1f} | P50: {sim['retraso_p50']:.0f} "
          f"| P80: {sim['retraso_p80']:.0f} | P90: {sim['retraso_p90']:.0f}")

    print(f"\nReserva de contingencia recomendada ({cont['criterio']}): ${cont['reserva_usd']:,.0f}", end="")
    print(f"  ({cont['reserva_pct']}% del costo base)" if "reserva_pct" in cont else "")
