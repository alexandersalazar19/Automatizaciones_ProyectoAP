import sys
from pathlib import Path
import pandas as pd

COLUMNAS_RECURSOS=["recurso","perfil","tipo","tarifa_hora_usd","horas_sprint","sprints"]
COLUMNAS_ADQUISICIONES=["concepto","categoria","costo_total_usd","sprints"]
TIPOS_RECURSO=["Planta","Contrato","Externo"]
SPRINTS_TOTAL=13
SEMANAS_POR_SPRINT=2
RELEASES={"R1":(1,5),"R2":(6,7),"R3":(8,11),"R4":(12,13)}  #sprints de cada release segun el informe
GRUPOS_DIRECTOS=["Recursos humanos","Servicios externos","Tecnologia y licencias"]
GRUPOS=GRUPOS_DIRECTOS+["Indirectos","Contingencia"]
COLUMNAS_DETALLE=["sprint","grupo","concepto","tipo","tarifa_hora_usd","horas","costo_usd"]

def parsearSprints(texto,maximo:int=SPRINTS_TOTAL)->list:
    #Acepta rangos y listas: "1-13", "8", "2;5;6;8", "1-3;7"
    sprints=set()
    for parte in str(texto).replace(" ","").split(";"):
        if not parte: continue
        if "-" in parte:
            ini,fin=parte.split("-")
            sprints.update(range(int(ini),int(fin)+1))
        else: sprints.add(int(parte))
    if not sprints: raise ValueError("Hay una fila sin sprints")
    if min(sprints)<1 or max(sprints)>maximo: raise ValueError(f"Los sprints deben estar entre 1 y {maximo}: '{texto}'")
    return sorted(sprints)

def validarColumnas(df:pd.DataFrame,columnas:list,nombre:str):
    faltantes=[c for c in columnas if c not in df.columns]
    if faltantes: raise ValueError(f"Faltan columnas en {nombre}: {faltantes}")

def cargarRecursos(ruta)->pd.DataFrame:
    df=pd.read_csv(ruta,dtype={"sprints":str})
    validarColumnas(df,COLUMNAS_RECURSOS,"recursos")
    if not df["tipo"].isin(TIPOS_RECURSO).all(): raise ValueError(f"'tipo' debe ser uno de: {TIPOS_RECURSO}")
    for col in ("tarifa_hora_usd","horas_sprint"):
        if (pd.to_numeric(df[col],errors="coerce").isna()|(df[col]<0)).any(): raise ValueError(f"'{col}' debe ser un numero mayor o igual a 0")
    df["sprints"].apply(parsearSprints)  #valida el formato de todas las filas
    return df

def cargarAdquisiciones(ruta)->pd.DataFrame:
    df=pd.read_csv(ruta,dtype={"sprints":str})
    validarColumnas(df,COLUMNAS_ADQUISICIONES,"adquisiciones")
    if (pd.to_numeric(df["costo_total_usd"],errors="coerce").isna()|(df["costo_total_usd"]<0)).any(): raise ValueError("'costo_total_usd' debe ser un numero mayor o igual a 0")
    df["sprints"].apply(parsearSprints)
    return df

def costosRecursos(df:pd.DataFrame,aplicarTarifasPlanta:bool=True)->pd.DataFrame:
    #Costo = tarifa x horas por sprint. Si no se aplican tarifas, el personal de planta cuesta 0
    filas=[]
    for _,r in df.iterrows():
        tarifa=0.0 if (r["tipo"]=="Planta" and not aplicarTarifasPlanta) else float(r["tarifa_hora_usd"])
        grupo="Servicios externos" if r["tipo"]=="Externo" else "Recursos humanos"
        for s in parsearSprints(r["sprints"]):
            filas.append({"sprint":s,"grupo":grupo,"concepto":r["recurso"],"tipo":r["tipo"],"tarifa_hora_usd":float(r["tarifa_hora_usd"]),
                          "horas":float(r["horas_sprint"]),"costo_usd":tarifa*float(r["horas_sprint"])})
    return pd.DataFrame(filas,columns=COLUMNAS_DETALLE)

def costosAdquisiciones(df:pd.DataFrame)->pd.DataFrame:
    #El costo total se reparte en partes iguales entre los sprints indicados
    filas=[]
    for _,r in df.iterrows():
        sprints=parsearSprints(r["sprints"])
        grupo="Servicios externos" if r["categoria"]=="Servicios externos" else "Tecnologia y licencias"
        for s in sprints:
            filas.append({"sprint":s,"grupo":grupo,"concepto":r["concepto"],"tipo":"Adquisicion","tarifa_hora_usd":None,
                          "horas":0.0,"costo_usd":float(r["costo_total_usd"])/len(sprints)})
    return pd.DataFrame(filas,columns=COLUMNAS_DETALLE)

def construirPresupuesto(recursos:pd.DataFrame,adquisiciones:pd.DataFrame,aplicarTarifasPlanta:bool=True,
                         indirectosPct:float=0.08,contingenciaModo:str="porcentaje",contingenciaPct:float=0.15,
                         contingenciaUsd:float=0.0)->dict:
    #contingenciaModo: "porcentaje" (sobre el costo base) o "riesgos" (monto USD tomado de la simulacion de riesgos)
    detalle=pd.concat([costosRecursos(recursos,aplicarTarifasPlanta),costosAdquisiciones(adquisiciones)],ignore_index=True)
    sprints=range(1,SPRINTS_TOTAL+1)

    tabla=detalle.pivot_table(index="sprint",columns="grupo",values="costo_usd",aggfunc="sum",fill_value=0.0)
    tabla=tabla.reindex(index=sprints,columns=GRUPOS_DIRECTOS,fill_value=0.0)

    directo=tabla.sum(axis=1)
    tabla["Indirectos"]=directo*indirectosPct
    base=tabla.sum(axis=1)

    if contingenciaModo=="riesgos": reserva=float(contingenciaUsd)
    else: reserva=float(base.sum())*contingenciaPct
    #La reserva se distribuye en el tiempo proporcionalmente al costo base de cada sprint
    tabla["Contingencia"]=base/base.sum()*reserva if base.sum()>0 else 0.0

    tabla["Total"]=tabla[GRUPOS].sum(axis=1)
    tabla["Acumulado"]=tabla["Total"].cumsum()
    tabla.index.name="sprint"

    return{
        "detalle":detalle,
        "tabla":tabla,
        "totalesPorGrupo":tabla[GRUPOS].sum(),
        "costoDirecto":float(directo.sum()),
        "indirectos":float(tabla["Indirectos"].sum()),
        "costoBase":float(base.sum()),
        "contingencia":float(tabla["Contingencia"].sum()),
        "presupuestoTotal":float(tabla["Total"].sum()),
        "contingenciaPctBase":float(tabla["Contingencia"].sum()/base.sum()) if base.sum()>0 else 0.0
    }

def costoPorRelease(tabla:pd.DataFrame)->pd.DataFrame:
    total=float(tabla["Total"].sum())
    filas=[]
    for release,(ini,fin) in RELEASES.items():
        costo=float(tabla.loc[ini:fin,"Total"].sum())
        filas.append({"release":release,"sprints":f"{ini}-{fin}","semanas":(fin-ini+1)*SEMANAS_POR_SPRINT,
                      "costo_usd":costo,"porcentaje":costo/total if total>0 else 0.0})
    return pd.DataFrame(filas)

def costoPorConcepto(detalle:pd.DataFrame)->pd.DataFrame:
    return (detalle.groupby(["grupo","concepto"],as_index=False)[["horas","costo_usd"]].sum()
            .sort_values("costo_usd",ascending=False).reset_index(drop=True))

def analisisFinanciero(presupuestoTotal:float,beneficioAnual:float,costoOperacionAnual:float,
                       tasaDescuento:float=0.10,horizonteAnios:int=3)->dict:
    #La inversion se hace en el anio 0 (26 semanas de proyecto); los beneficios netos empiezan al lanzar
    neto=beneficioAnual-costoOperacionAnual
    flujos=[-presupuestoTotal]+[neto]*horizonteAnios
    vpFlujos=[f/(1+tasaDescuento)**t for t,f in enumerate(flujos)]
    vpBeneficios=sum(neto/(1+tasaDescuento)**t for t in range(1,horizonteAnios+1))
    factorAnualidad=sum(1/(1+tasaDescuento)**t for t in range(1,horizonteAnios+1))
    return{
        "flujos":flujos,
        "vpFlujos":vpFlujos,
        "van":sum(vpFlujos),
        "roi":(neto*horizonteAnios-presupuestoTotal)/presupuestoTotal if presupuestoTotal>0 else 0.0,
        "relacionBC":vpBeneficios/presupuestoTotal if presupuestoTotal>0 else 0.0,
        "paybackMeses":presupuestoTotal/neto*12 if neto>0 else None,
        "beneficioNetoAnual":neto,
        #Beneficio anual bruto necesario para que el VAN sea 0 (punto de equilibrio)
        "beneficioEquilibrio":costoOperacionAnual+presupuestoTotal/factorAnualidad if factorAnualidad>0 else None
    }

def reservaDesdeRiesgos(archivoRiesgos,percentil:str="costo_p80",iteraciones:int=10000,semilla:int=42)->dict:
    #Usa el motor de la automatizacion de riesgos (carpeta Riesgos, al lado de esta carpeta Costos)
    padre=Path(__file__).resolve().parent.parent
    carpetas=[c for c in padre.iterdir() if c.is_dir() and c.name.lower()=="riesgos"]
    if not carpetas: raise ImportError("No se encontro la carpeta Riesgos junto a la carpeta Costos")
    if str(carpetas[0]) not in sys.path: sys.path.append(str(carpetas[0]))
    try: import motorRiesgos
    except ImportError as e: raise ImportError("No se encontro motorRiesgos.py dentro de la carpeta Riesgos") from e
    df=motorRiesgos.cargarRiesgos(archivoRiesgos)
    sim=motorRiesgos.simular(df,iteraciones,semilla)
    return{"reserva_usd":float(sim[percentil]),"riesgosActivos":len(motorRiesgos.riesgosActivos(df)),"percentil":percentil}

if __name__=="__main__":
    base=Path(__file__).parent
    rutaRecursos=sys.argv[1] if len(sys.argv)>1 else base/"recursos.csv"
    rutaAdquisiciones=sys.argv[2] if len(sys.argv)>2 else base/"adquisiciones.csv"

    recursos=cargarRecursos(rutaRecursos)
    adquisiciones=cargarAdquisiciones(rutaAdquisiciones)
    p=construirPresupuesto(recursos,adquisiciones)

    print("\n=== Costo por sprint (USD) ===")
    print(p["tabla"].round(0).astype(int).to_string())

    print("\n=== Totales por grupo ===")
    print(p["totalesPorGrupo"].round(0).astype(int).to_string())
    print(f"\nCosto directo: ${p['costoDirecto']:,.0f} | Indirectos: ${p['indirectos']:,.0f} | Costo base: ${p['costoBase']:,.0f}")
    print(f"Contingencia: ${p['contingencia']:,.0f} ({p['contingenciaPctBase']*100:.1f}% del costo base)")
    print(f"PRESUPUESTO TOTAL: ${p['presupuestoTotal']:,.0f}")

    print("\n=== Costo por release ===")
    print(costoPorRelease(p["tabla"]).round(2).to_string(index=False))

    f=analisisFinanciero(p["presupuestoTotal"],65000,20000)
    print(f"\n=== Analisis financiero (supuestos de ejemplo) ===")
    print(f"VAN: ${f['van']:,.0f} | ROI: {f['roi']*100:.1f}% | B/C: {f['relacionBC']:.2f} | Recuperacion: {f['paybackMeses']:.1f} meses")
    print(f"Beneficio anual necesario para VAN=0: ${f['beneficioEquilibrio']:,.0f}")