import sys
from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment,Border,Font,PatternFill,Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from Riesgos.motorRiesgos import PROB_PORCENTAJE,cargarRiesgos,contingencia,simular

FUENTE="Arial"
NIVELES=["Critico","Alto","Medio","Bajo"]
UMBRALES={"Critico":16,"Alto":10,"Medio":5}
RELLENO_SUAVE={"Critico":"F4A6A6","Alto":"F9C98B","Medio":"FBE9A0","Bajo":"B9E0B3"}
RELLENO_FUERTE={"Critico":"D62728","Alto":"FF7F0E","Medio":"F2C200","Bajo":"2CA02C"}
HOJA="'Matriz de riesgos'"
LADO=Side(style="thin",color="BFBFBF")
BORDE=Border(left=LADO,right=LADO,top=LADO,bottom=LADO)
COLUMNAS_TABLA=[("id",8),("riesgo",42),("categoria",14),("causa",34),("probabilidad",13),("impacto",10),
                ("puntaje",10),("nivel",11),("prob_pct",10),("costo_usd",13),("retraso_sprints",15),
                ("vme_usd",13),("vme_sprints",13),("estrategia",13),("accion_respuesta",48),
                ("responsable",22),("sprint_afectado",14),("estado",11)]
LETRA={nombre:get_column_letter(i+1) for i,(nombre,_) in enumerate(COLUMNAS_TABLA)}

def fuente(negrita=False,color="000000",tam=10)->Font:
    return Font(name=FUENTE,bold=negrita,color=color,size=tam)

def nivelDe(puntaje:int)->str:
    for nivel,minimo in UMBRALES.items():
        if puntaje>=minimo: return nivel
    return "Bajo"

def estilizarEncabezado(celda):
    celda.font=fuente(True,"FFFFFF")
    celda.fill=PatternFill("solid",fgColor="1F3864")
    celda.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
    celda.border=BORDE

def hojaParametros(wb:Workbook):
    ws=wb.create_sheet("Parametros")
    ws["A1"]="Probabilidad (1-5)"
    ws["B1"]="Porcentaje"
    for celda in (ws["A1"],ws["B1"]): estilizarEncabezado(celda)
    for fila,(escala,pct) in enumerate(PROB_PORCENTAJE.items(),start=2):
        ws.cell(fila,1,escala)
        celda=ws.cell(fila,2,pct)
        celda.number_format="0%"
        celda.font=fuente(color="0000FF") #azul: valor de entrada editable
    ws["A8"]="Nivel"
    ws["B8"]="Puntaje minimo"
    for celda in (ws["A8"],ws["B8"]): estilizarEncabezado(celda)
    for fila,(nivel,minimo) in enumerate(UMBRALES.items(),start=9):
        ws.cell(fila,1,nivel)
        ws.cell(fila,2,minimo).font=fuente(color="0000FF")
    ws["A12"]="Bajo"
    ws["B12"]="Menor al umbral de Medio"
    ws["A14"]=("Los valores en azul se pueden editar: la matriz de riesgos recalcula automaticamente "
               "el porcentaje, el puntaje, el nivel y el valor monetario esperado.")
    ws["A14"].alignment=Alignment(wrap_text=True,vertical="top")
    ws.merge_cells("A14:B16")
    ws.column_dimensions["A"].width=22
    ws.column_dimensions["B"].width=26

def hojaMatriz(wb:Workbook,df:pd.DataFrame)->int:
    ws=wb.create_sheet("Matriz de riesgos")
    for col,(nombre,ancho) in enumerate(COLUMNAS_TABLA,start=1):
        celda=ws.cell(1,col,nombre)
        estilizarEncabezado(celda)
        ws.column_dimensions[get_column_letter(col)].width=ancho
    ws.row_dimensions[1].height=32

    L=LETRA
    for fila,(_,r) in enumerate(df.iterrows(),start=2):
        valores={"id":r["id"],"riesgo":r["riesgo"],"categoria":r["categoria"],"causa":r["causa"],
                 "probabilidad":int(r["probabilidad"]),"impacto":int(r["impacto"]),
                 "puntaje":f"={L['probabilidad']}{fila}*{L['impacto']}{fila}",
                 "nivel":(f"=IF({L['puntaje']}{fila}>=Parametros!$B$9,\"Critico\","
                          f"IF({L['puntaje']}{fila}>=Parametros!$B$10,\"Alto\","
                          f"IF({L['puntaje']}{fila}>=Parametros!$B$11,\"Medio\",\"Bajo\")))"),
                 "prob_pct":f"=INDEX(Parametros!$B$2:$B$6,{L['probabilidad']}{fila})",
                 "costo_usd":float(r["costo_usd"]),"retraso_sprints":float(r["retraso_sprints"]),
                 "vme_usd":f"={L['prob_pct']}{fila}*{L['costo_usd']}{fila}",
                 "vme_sprints":f"={L['prob_pct']}{fila}*{L['retraso_sprints']}{fila}",
                 "estrategia":r["estrategia"],"accion_respuesta":r["accion_respuesta"],
                 "responsable":r["responsable"],"sprint_afectado":int(r["sprint_afectado"]),"estado":r["estado"]}
        for col,(nombre,_) in enumerate(COLUMNAS_TABLA,start=1):
            celda=ws.cell(fila,col,valores[nombre])
            celda.font=fuente(color="0000FF" if nombre in ("probabilidad","impacto","costo_usd","retraso_sprints") else "000000")
            celda.border=BORDE
            celda.alignment=Alignment(vertical="top",wrap_text=nombre in ("riesgo","causa","accion_respuesta"),
                                      horizontal="center" if nombre in ("id","probabilidad","impacto","puntaje","nivel","prob_pct","sprint_afectado") else None)
            if nombre in ("costo_usd","vme_usd"): celda.number_format="$#,##0"
            if nombre=="prob_pct": celda.number_format="0%"
            if nombre in ("vme_sprints",): celda.number_format="0.00"

    ultima=len(df)+1
    rango=f"{L['nivel']}2:{L['nivel']}{ultima}"
    for nivel in NIVELES:
        ws.conditional_formatting.add(rango,CellIsRule(operator="equal",formula=[f'"{nivel}"'],
                                      fill=PatternFill("solid",bgColor=RELLENO_SUAVE[nivel],fgColor=RELLENO_SUAVE[nivel])))
    ws.freeze_panes="C2"
    ws.auto_filter.ref=f"A1:{get_column_letter(len(COLUMNAS_TABLA))}{ultima}"
    return ultima

def hojaMapaCalor(wb:Workbook,df:pd.DataFrame):
    ws=wb.create_sheet("Mapa de calor")
    ws["A1"]="Mapa de calor de riesgos (probabilidad x impacto)"
    ws["A1"].font=fuente(True,tam=13)
    ws["A2"]="Cada celda lista los ID de los riesgos con esa probabilidad e impacto (fotografia al momento de exportar)."
    ws["A2"].font=fuente(color="595959")

    ws["B4"]="IMPACTO"
    ws["B4"].font=fuente(True)
    ws.merge_cells("B4:F4")
    ws["B4"].alignment=Alignment(horizontal="center")
    for i in range(1,6):
        celda=ws.cell(5,i+1,i)
        estilizarEncabezado(celda)
        ws.column_dimensions[get_column_letter(i+1)].width=20
    ws.column_dimensions["A"].width=16

    ws["A11"]="PROBABILIDAD"
    for fila,p in enumerate(range(5,0,-1),start=6):
        etiqueta=ws.cell(fila,1,p)
        estilizarEncabezado(etiqueta)
        ws.row_dimensions[fila].height=58
        for i in range(1,6):
            ids=df[(df["probabilidad"]==p)&(df["impacto"]==i)]["id"].tolist()
            nivel=nivelDe(p*i)
            celda=ws.cell(fila,i+1,"\n".join(ids))
            celda.fill=PatternFill("solid",fgColor=RELLENO_FUERTE[nivel])
            celda.font=fuente(True,"FFFFFF" if nivel in ("Critico","Bajo") else "000000")
            celda.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
            celda.border=BORDE
    ws["A11"].font=fuente(True)
    ws["A11"].alignment=Alignment(wrap_text=True,vertical="center")

    ws["A13"]="Leyenda"
    ws["A13"].font=fuente(True)
    for fila,nivel in enumerate(NIVELES,start=14):
        celda=ws.cell(fila,1,nivel)
        celda.fill=PatternFill("solid",fgColor=RELLENO_FUERTE[nivel])
        celda.font=fuente(True,"FFFFFF" if nivel in ("Critico","Bajo") else "000000")
        celda.alignment=Alignment(horizontal="center")

def hojaResumen(wb:Workbook,sim:dict,cont:dict,costoBase:float,semilla:int,percentil:str,ultima:int):
    ws=wb["Resumen"]
    L=LETRA
    estado=f"{HOJA}!${L['estado']}$2:${L['estado']}${ultima}"
    nivel=f"{HOJA}!${L['nivel']}$2:${L['nivel']}${ultima}"
    vme=f"{HOJA}!${L['vme_usd']}$2:${L['vme_usd']}${ultima}"
    activos='{0},"<>Mitigado",{0},"<>Cerrado"'

    def titulo(celda,texto):
        ws[celda]=texto
        ws[celda].font=fuente(True,tam=12)

    ws["A1"]="Resumen de gestion de riesgos - Amparo IA"
    ws["A1"].font=fuente(True,tam=14)

    titulo("A3","Parametros de la simulacion")
    parametros=[("Iteraciones",sim["iteraciones"],"#,##0"),("Semilla aleatoria",semilla,"0"),
                ("Costo base del proyecto (USD)",costoBase,"$#,##0"),
                ("Percentil de contingencia",percentil.replace("costo_","").upper(),"@")]
    for fila,(nombre,valor,formato) in enumerate(parametros,start=4):
        ws.cell(fila,1,nombre)
        celda=ws.cell(fila,2,valor)
        celda.number_format=formato
        celda.font=fuente(color="0000FF")
        celda.alignment=Alignment(horizontal="right")

    titulo("A9","Riesgos activos por nivel")
    for fila,n in enumerate(NIVELES,start=10):
        ws.cell(fila,1,n)
        ws.cell(fila,2,f'=COUNTIFS({nivel},A{fila},{activos.format(estado)})')
    ws["A14"]="Total de riesgos activos"
    ws["B14"]="=SUM(B10:B13)"
    ws["A14"].font=fuente(True)
    ws["B14"].font=fuente(True)

    titulo("A16","Valor monetario esperado (VME)")
    ws["A17"]="VME total de riesgos activos (USD)"
    ws["B17"]=f"=SUMIFS({vme},{activos.format(estado)})"
    ws["B17"].number_format="$#,##0"

    titulo("A19","Resultados de la simulacion Monte Carlo")
    for col,texto in enumerate(["Indicador","Costo de riesgos (USD)","Retraso (sprints)"],start=1):
        estilizarEncabezado(ws.cell(20,col,texto))
    filas=[("Media","costo_medio","retraso_medio"),("P50","costo_p50","retraso_p50"),
           ("P80","costo_p80","retraso_p80"),("P90","costo_p90","retraso_p90")]
    for fila,(nombre,kc,kr) in enumerate(filas,start=21):
        ws.cell(fila,1,nombre)
        ws.cell(fila,2,round(sim[kc],2)).number_format="$#,##0"
        ws.cell(fila,3,round(sim[kr],2)).number_format="0.0"

    titulo("A26","Reserva de contingencia recomendada")
    ws["A27"]=f"Reserva ({cont['criterio'].replace('COSTO_','')}) en USD"
    ws["B27"]=cont["reserva_usd"]
    ws["B27"].number_format="$#,##0"
    ws["A28"]="Reserva como porcentaje del costo base"
    ws["B28"]='=IF(B6>0,B27/B6,"N/A")'
    ws["B28"].number_format="0.0%"

    ws["A30"]="Notas"
    ws["A30"].font=fuente(True)
    notas=["El percentil Pxx es el valor que el xx % de los escenarios simulados no supera.",
           "La simulacion se ejecuto en Python (motor.py): las filas 21 a 24 y la celda B27 son resultados fijos, no se recalculan en Excel.",
           "En la hoja Matriz de riesgos, puntaje, nivel, porcentaje y VME son formulas que dependen de la hoja Parametros.",
           "El retraso de riesgos del mismo release se solapa: dentro de cada release se toma el mayor retraso y luego se suman los releases.",
           "La reserva cubre solo los riesgos identificados; los riesgos no previstos requieren una reserva de gestion aparte."]
    for fila,nota in enumerate(notas,start=31):
        ws.cell(fila,1,nota).alignment=Alignment(wrap_text=False)

    ws.column_dimensions["A"].width=44
    ws.column_dimensions["B"].width=24
    ws.column_dimensions["C"].width=20

def normalizarFuentes(wb:Workbook):
    #Todo el libro en Arial, las celdas sin estilo propio quedan en tamano 10
    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for celda in fila:
                f=celda.font
                celda.font=Font(name=FUENTE,size=10 if f.size==11 else f.size,bold=f.bold,italic=f.italic,color=f.color)

def exportarExcel(df:pd.DataFrame,sim:dict,cont:dict,costoBase:float=0.0,semilla:int=42,percentil:str="costo_p80")->bytes:
    wb=Workbook()
    wb.active.title="Resumen"
    hojaParametros(wb)
    ultima=hojaMatriz(wb,df)
    hojaMapaCalor(wb,df)
    hojaResumen(wb,sim,cont,costoBase,semilla,percentil,ultima)
    wb.move_sheet("Parametros",offset=len(wb.sheetnames))
    normalizarFuentes(wb)
    for ws in wb.worksheets:
        ws.page_setup.orientation="landscape"
        ws.sheet_properties.pageSetUpPr=PageSetupProperties(fitToPage=True)
        ws.page_setup.fitToWidth=1
        ws.page_setup.fitToHeight=0
    salida=BytesIO()
    wb.save(salida)
    return salida.getvalue()

if __name__=="__main__":
    ruta=sys.argv[1] if len(sys.argv)>1 else "riesgos.csv"
    salida=sys.argv[2] if len(sys.argv)>2 else "matriz_riesgos.xlsx"
    base=float(sys.argv[3]) if len(sys.argv)>3 else 0.0

    datos=cargarRiesgos(ruta)
    sim=simular(datos)
    cont=contingencia(sim,base)
    with open(salida,"wb") as f: f.write(exportarExcel(datos,sim,cont,base))
    print(f"Excel generado: {salida}")