from io import BytesIO
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart,LineChart,Reference
from openpyxl.styles import Alignment,Border,Font,PatternFill,Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties
from motorCostos import GRUPOS_DIRECTOS,RELEASES,SEMANAS_POR_SPRINT,SPRINTS_TOTAL,costoPorConcepto

FUENTE="Arial"
LADO=Side(style="thin",color="BFBFBF")
BORDE=Border(left=LADO,right=LADO,top=LADO,bottom=LADO)
FORMATO_USD="$#,##0"

#Filas de la hoja Resumen (las formulas de las otras hojas dependen de estas posiciones)
R={"aplicar":4,"indir":5,"modo":6,"pct":7,"monto":8,
   "rrhh":11,"serv":12,"tec":13,"directo":14,"indirectos":15,"base":16,"conting":17,"total":18,"contPct":19,"verif":20,
   "benef":23,"costoOp":24,"tasa":25,"hor":26,"neto":27,"factor":28,"van":29,"roi":30,"bc":31,"payback":32,"equilibrio":33}
FILA_TOTAL=SPRINTS_TOTAL+2  #fila de totales en la hoja Distribucion

def fuente(negrita=False,color="000000",tam=10)->Font:
    return Font(name=FUENTE,bold=negrita,color=color,size=tam)

def encabezado(celda):
    celda.font=fuente(True,"FFFFFF")
    celda.fill=PatternFill("solid",fgColor="1F3864")
    celda.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
    celda.border=BORDE

def releaseDe(sprint:int)->str:
    for release,(ini,fin) in RELEASES.items():
        if ini<=sprint<=fin: return release
    return ""

def hojaDetalle(wb:Workbook,detalle:pd.DataFrame)->int:
    ws=wb.create_sheet("Detalle")
    columnas=[("sprint",9),("grupo",24),("concepto",46),("tipo",13),("tarifa_hora_usd",16),("horas",10),("costo_usd",14)]
    for col,(nombre,ancho) in enumerate(columnas,start=1):
        encabezado(ws.cell(1,col,nombre))
        ws.column_dimensions[get_column_letter(col)].width=ancho
    ws.row_dimensions[1].height=30

    for fila,(_,r) in enumerate(detalle.iterrows(),start=2):
        esRecurso=r["tipo"]!="Adquisicion"
        valores=[int(r["sprint"]),r["grupo"],r["concepto"],r["tipo"],
                 float(r["tarifa_hora_usd"]) if esRecurso else None,float(r["horas"]),
                 f'=IF(AND(D{fila}="Planta",Resumen!$B${R["aplicar"]}="No"),0,E{fila}*F{fila})' if esRecurso else float(r["costo_usd"])]
        for col,valor in enumerate(valores,start=1):
            celda=ws.cell(fila,col,valor)
            celda.border=BORDE
            celda.font=fuente(color="0000FF" if col in (5,6) or (col==7 and not esRecurso) else "000000")
            if col==5: celda.number_format="$#,##0.00"
            if col==7: celda.number_format="$#,##0.00"
    ultima=len(detalle)+1
    ws.freeze_panes="A2"
    ws.auto_filter.ref=f"A1:G{ultima}"
    return ultima

def hojaDistribucion(wb:Workbook,ultimaDetalle:int):
    ws=wb.create_sheet("Distribucion")
    columnas=["sprint","release"]+GRUPOS_DIRECTOS+["Indirectos","Contingencia","Total","Acumulado"]
    for col,nombre in enumerate(columnas,start=1):
        encabezado(ws.cell(1,col,nombre))
        ws.column_dimensions[get_column_letter(col)].width=14 if col<=2 else 20
    ws.row_dimensions[1].height=30

    rangoSprint=f"Detalle!$A$2:$A${ultimaDetalle}"
    rangoGrupo=f"Detalle!$B$2:$B${ultimaDetalle}"
    rangoCosto=f"Detalle!$G$2:$G${ultimaDetalle}"
    for s in range(1,SPRINTS_TOTAL+1):
        f=s+1
        ws.cell(f,1,s)
        ws.cell(f,2,releaseDe(s))
        for col,letra in zip((3,4,5),("C","D","E")):
            ws.cell(f,col,f"=SUMIFS({rangoCosto},{rangoSprint},$A{f},{rangoGrupo},{letra}$1)")
        ws.cell(f,6,f"=SUM(C{f}:E{f})*Resumen!$B${R['indir']}")
        ws.cell(f,7,f"=IF(Resumen!$B${R['base']}>0,SUM(C{f}:F{f})/Resumen!$B${R['base']}*Resumen!$B${R['conting']},0)")
        ws.cell(f,8,f"=SUM(C{f}:G{f})")
        ws.cell(f,9,f"=SUM($H$2:H{f})")
        for col in range(1,10):
            celda=ws.cell(f,col)
            celda.border=BORDE
            celda.font=fuente()
            if col>=3: celda.number_format=FORMATO_USD
            if col<=2: celda.alignment=Alignment(horizontal="center")

    ws.cell(FILA_TOTAL,1,"Total")
    for col in range(3,9):
        letra=get_column_letter(col)
        ws.cell(FILA_TOTAL,col,f"=SUM({letra}2:{letra}{SPRINTS_TOTAL+1})")
    for col in range(1,10):
        celda=ws.cell(FILA_TOTAL,col)
        celda.font=fuente(True)
        celda.border=BORDE
        celda.fill=PatternFill("solid",fgColor="D9E1F2")
        if col>=3: celda.number_format=FORMATO_USD
    ws.freeze_panes="C2"

    #Grafico de barras apiladas por sprint
    barras=BarChart()
    barras.type="col"
    barras.grouping="stacked"
    barras.overlap=100
    barras.title="Costo por sprint y grupo (USD)"
    barras.y_axis.title="USD"
    barras.x_axis.title="Sprint"
    barras.add_data(Reference(ws,min_col=3,max_col=7,min_row=1,max_row=SPRINTS_TOTAL+1),titles_from_data=True)
    barras.set_categories(Reference(ws,min_col=1,min_row=2,max_row=SPRINTS_TOTAL+1))
    barras.height=9
    barras.width=20
    barras.x_axis.delete=False
    barras.y_axis.delete=False
    ws.add_chart(barras,"K2")

    #Curva S (costo acumulado)
    linea=LineChart()
    linea.title="Costo acumulado - curva S (USD)"
    linea.y_axis.title="USD"
    linea.x_axis.title="Sprint"
    linea.add_data(Reference(ws,min_col=9,min_row=1,max_row=SPRINTS_TOTAL+1),titles_from_data=True)
    linea.set_categories(Reference(ws,min_col=1,min_row=2,max_row=SPRINTS_TOTAL+1))
    linea.height=9
    linea.width=20
    linea.x_axis.delete=False
    linea.y_axis.delete=False
    ws.add_chart(linea,"K22")

def hojaRelease(wb:Workbook):
    ws=wb.create_sheet("Por release")
    for col,(nombre,ancho) in enumerate([("release",12),("sprints",12),("semanas",12),("costo_usd",16),("porcentaje",14)],start=1):
        encabezado(ws.cell(1,col,nombre))
        ws.column_dimensions[get_column_letter(col)].width=ancho
    rangoRelease=f"Distribucion!$B$2:$B${SPRINTS_TOTAL+1}"
    rangoTotal=f"Distribucion!$H$2:$H${SPRINTS_TOTAL+1}"
    for fila,(release,(ini,fin)) in enumerate(RELEASES.items(),start=2):
        ws.cell(fila,1,release)
        ws.cell(fila,2,f"{ini}-{fin}")
        ws.cell(fila,3,(fin-ini+1)*SEMANAS_POR_SPRINT)
        ws.cell(fila,4,f"=SUMIFS({rangoTotal},{rangoRelease},A{fila})").number_format=FORMATO_USD
        ws.cell(fila,5,f"=IF(Distribucion!$H${FILA_TOTAL}>0,D{fila}/Distribucion!$H${FILA_TOTAL},0)").number_format="0.0%"
        for col in range(1,6):
            ws.cell(fila,col).border=BORDE
            ws.cell(fila,col).font=fuente()
            if col<=3: ws.cell(fila,col).alignment=Alignment(horizontal="center")
    fin=len(RELEASES)+2
    ws.cell(fin,1,"Total")
    ws.cell(fin,4,f"=SUM(D2:D{fin-1})").number_format=FORMATO_USD
    ws.cell(fin,5,f"=SUM(E2:E{fin-1})").number_format="0.0%"
    for col in range(1,6):
        ws.cell(fin,col).font=fuente(True)
        ws.cell(fin,col).border=BORDE
        ws.cell(fin,col).fill=PatternFill("solid",fgColor="D9E1F2")

def hojaConceptos(wb:Workbook,detalle:pd.DataFrame,ultimaDetalle:int):
    ws=wb.create_sheet("Por concepto")
    for col,(nombre,ancho) in enumerate([("concepto",48),("grupo",24),("horas",12),("costo_usd",16)],start=1):
        encabezado(ws.cell(1,col,nombre))
        ws.column_dimensions[get_column_letter(col)].width=ancho
    rangoConcepto=f"Detalle!$C$2:$C${ultimaDetalle}"
    for fila,(_,r) in enumerate(costoPorConcepto(detalle).iterrows(),start=2):
        ws.cell(fila,1,r["concepto"])
        ws.cell(fila,2,r["grupo"])
        ws.cell(fila,3,f"=SUMIFS(Detalle!$F$2:$F${ultimaDetalle},{rangoConcepto},A{fila})").number_format="#,##0"
        ws.cell(fila,4,f"=SUMIFS(Detalle!$G$2:$G${ultimaDetalle},{rangoConcepto},A{fila})").number_format=FORMATO_USD
        for col in range(1,5):
            ws.cell(fila,col).border=BORDE
            ws.cell(fila,col).font=fuente()
    ws.freeze_panes="A2"

def hojaResumen(wb:Workbook,params:dict):
    ws=wb["Resumen"]
    entrada=lambda celda:setattr(celda,"font",fuente(color="0000FF"))

    ws["A1"]="Presupuesto del proyecto - Amparo IA"
    ws["A1"].font=fuente(True,tam=14)
    ws["A2"]="Las celdas en azul son parametros editables: todo el libro se recalcula al cambiarlas."
    ws["A2"].font=fuente(color="595959")

    ws["A3"]="Parametros"
    ws["A3"].font=fuente(True,tam=12)
    ws.cell(R["aplicar"],1,"Aplicar tarifas al personal de planta (Si/No)")
    ws.cell(R["aplicar"],2,"Si" if params["aplicarTarifasPlanta"] else "No")
    ws.cell(R["indir"],1,"Costos indirectos (% del costo directo)")
    ws.cell(R["indir"],2,params["indirectosPct"]).number_format="0.0%"
    ws.cell(R["modo"],1,"Modo de la reserva de contingencia (Porcentaje/Riesgos)")
    ws.cell(R["modo"],2,"Riesgos" if params["contingenciaModo"]=="riesgos" else "Porcentaje")
    ws.cell(R["pct"],1,"Contingencia como % del costo base (modo Porcentaje)")
    ws.cell(R["pct"],2,params["contingenciaPct"]).number_format="0.0%"
    ws.cell(R["monto"],1,"Reserva desde la simulacion de riesgos, USD (modo Riesgos)")
    ws.cell(R["monto"],2,params["contingenciaUsd"]).number_format=FORMATO_USD
    for clave in ("aplicar","indir","modo","pct","monto"): entrada(ws.cell(R[clave],2))

    validacionSi=DataValidation(type="list",formula1='"Si,No"',allow_blank=False)
    validacionModo=DataValidation(type="list",formula1='"Porcentaje,Riesgos"',allow_blank=False)
    ws.add_data_validation(validacionSi)
    ws.add_data_validation(validacionModo)
    validacionSi.add(ws.cell(R["aplicar"],2))
    validacionModo.add(ws.cell(R["modo"],2))

    ws["A10"]="Presupuesto"
    ws["A10"].font=fuente(True,tam=12)
    f=FILA_TOTAL
    filas=[("rrhh","Recursos humanos",f"=Distribucion!C{f}"),("serv","Servicios externos",f"=Distribucion!D{f}"),
           ("tec","Tecnologia y licencias",f"=Distribucion!E{f}"),
           ("directo","Costo directo",f"=SUM(B{R['rrhh']}:B{R['tec']})"),
           ("indirectos","Costos indirectos",f"=B{R['directo']}*B{R['indir']}"),
           ("base","Costo base",f"=B{R['directo']}+B{R['indirectos']}"),
           ("conting","Reserva de contingencia",f'=IF(B{R["modo"]}="Porcentaje",B{R["base"]}*B{R["pct"]},B{R["monto"]})'),
           ("total","PRESUPUESTO TOTAL",f"=B{R['base']}+B{R['conting']}"),
           ("contPct","Contingencia como % del costo base",f"=IF(B{R['base']}>0,B{R['conting']}/B{R['base']},0)"),
           ("verif","Total segun la distribucion por sprint (verificacion)",f"=Distribucion!H{f}")]
    for clave,texto,formula in filas:
        ws.cell(R[clave],1,texto)
        celda=ws.cell(R[clave],2,formula)
        celda.number_format="0.0%" if clave=="contPct" else FORMATO_USD
    for clave in ("directo","base","total"):
        ws.cell(R[clave],1).font=fuente(True)
        ws.cell(R[clave],2).font=fuente(True)
    ws.cell(R["total"],1).fill=PatternFill("solid",fgColor="D9E1F2")
    ws.cell(R["total"],2).fill=PatternFill("solid",fgColor="D9E1F2")

    ws["A22"]="Analisis financiero basico (supuestos que el equipo debe justificar)"
    ws["A22"].font=fuente(True,tam=12)
    ws.cell(R["benef"],1,"Beneficio anual esperado (USD)")
    ws.cell(R["benef"],2,params["beneficioAnual"]).number_format=FORMATO_USD
    ws.cell(R["costoOp"],1,"Costo de operacion anual (USD)")
    ws.cell(R["costoOp"],2,params["costoOperacionAnual"]).number_format=FORMATO_USD
    ws.cell(R["tasa"],1,"Tasa de descuento anual")
    ws.cell(R["tasa"],2,params["tasaDescuento"]).number_format="0.0%"
    ws.cell(R["hor"],1,"Horizonte de evaluacion (anios)")
    ws.cell(R["hor"],2,params["horizonteAnios"])
    for clave in ("benef","costoOp","tasa","hor"): entrada(ws.cell(R[clave],2))

    t,b=R["total"],R["benef"]
    calculos=[("neto","Beneficio neto anual",f"=B{b}-B{R['costoOp']}",FORMATO_USD),
              ("factor","Factor de anualidad",f"=IF(B{R['tasa']}=0,B{R['hor']},(1-(1+B{R['tasa']})^(-B{R['hor']}))/B{R['tasa']})","0.000"),
              ("van","VAN (valor actual neto)",f"=-B{t}+B{R['neto']}*B{R['factor']}",FORMATO_USD),
              ("roi","ROI",f"=IF(B{t}>0,(B{R['neto']}*B{R['hor']}-B{t})/B{t},0)","0.0%"),
              ("bc","Relacion beneficio/costo",f"=IF(B{t}>0,B{R['neto']}*B{R['factor']}/B{t},0)","0.00"),
              ("payback","Recuperacion de la inversion (meses)",f'=IF(B{R["neto"]}>0,B{t}/B{R["neto"]}*12,"N/A")',"0.0"),
              ("equilibrio","Beneficio anual necesario para VAN = 0",f"=B{R['costoOp']}+B{t}/B{R['factor']}",FORMATO_USD)]
    for clave,texto,formula,formato in calculos:
        ws.cell(R[clave],1,texto)
        ws.cell(R[clave],2,formula).number_format=formato

    ws["A35"]="Notas"
    ws["A35"].font=fuente(True)
    notas=["Las tarifas por hora y las horas por sprint estan en la hoja Detalle (celdas en azul).",
           "Si el interruptor de tarifas esta en No, el personal de planta no genera costo; el contrato y los servicios externos si.",
           "La reserva de contingencia se reparte por sprint en proporcion al costo base de cada uno.",
           "El monto de la reserva en modo Riesgos proviene de la simulacion Monte Carlo de la automatizacion de riesgos.",
           "El analisis financiero supone que la inversion se realiza en el anio 0 y los beneficios netos empiezan al lanzar la plataforma."]
    for fila,nota in enumerate(notas,start=36): ws.cell(fila,1,nota)

    ws.column_dimensions["A"].width=58
    ws.column_dimensions["B"].width=20

def normalizarFuentes(wb:Workbook):
    for ws in wb.worksheets:
        for fila in ws.iter_rows():
            for celda in fila:
                f=celda.font
                celda.font=Font(name=FUENTE,size=10 if f.size==11 else f.size,bold=f.bold,italic=f.italic,color=f.color)

def exportarExcel(recursos:pd.DataFrame,adquisiciones:pd.DataFrame,params:dict,presupuesto:dict)->bytes:
    #params: aplicarTarifasPlanta, indirectosPct, contingenciaModo, contingenciaPct, contingenciaUsd,
    #        beneficioAnual, costoOperacionAnual, tasaDescuento, horizonteAnios
    detalle=presupuesto["detalle"]
    wb=Workbook()
    wb.active.title="Resumen"
    ultima=hojaDetalle(wb,detalle)
    hojaDistribucion(wb,ultima)
    hojaRelease(wb)
    hojaConceptos(wb,detalle,ultima)
    hojaResumen(wb,params)
    wb.move_sheet("Detalle",offset=len(wb.sheetnames))  #Detalle queda al final
    normalizarFuentes(wb)
    for ws in wb.worksheets:
        ws.page_setup.orientation="landscape"
        ws.sheet_properties.pageSetUpPr=PageSetupProperties(fitToPage=True)
        ws.page_setup.fitToWidth=1
        ws.page_setup.fitToHeight=0
    salida=BytesIO()
    wb.save(salida)
    return salida.getvalue()