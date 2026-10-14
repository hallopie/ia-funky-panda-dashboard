"""Clasificador propuesto de movimientos bancarios (aprende de la clasificación de agosto de Mario).
classify(row) -> dict(cat, trat, fp, conf, regla). fp: 'Sí' | 'No' | 'Revisar'. conf: 'alta' | 'media' | 'baja'.
Solo se aplica al dashboard lo de confianza alta/media con fp Sí/No; lo demás queda 'Sin clasificar'.
Categorías de Mario: Fijos, Insumos, Variables, Operaciones, RDSS, Comisión bancaria.
"""
import re

# (regex sobre subcategoría+concepto en minúsculas, sucursales, cat, trat, fp, conf, bucket)
R = []
def r(rx, br, cat, trat, fp, conf, bucket, nota=''):
    R.append((re.compile(rx, re.I), br, cat, trat, fp, conf, bucket, nota))

# --- Brisas: nómina (nombres de la tabla de nómina de Brisas) ---
r(r'uriel|kaire|\bkai\b|elias salinas|erick ismael|oscar arturo|araceli|\bmimi\b|noemi|diego hernandez|norma garcia|luis roberto|israel valle|roger garcia|\bjazz?\b|\bjaz\b|christian hern', 'B', 'Fijos', 'Nómina', 'Sí', 'alta', 'Nómina')
# --- Brisas: insumos ---
r(r'edwin fuorvia|liah|angel tenorio|verduras brisas|mariscos|uscanga|soriana|fresko|mercado libre|costco|proteina|toyo|refresco|carniceria|abarrotes', 'B', 'Insumos', 'Insumos', 'Sí', 'alta', 'Insumos')
# --- RDSS / marketing ---
r(r'mauricio ramos', 'B', 'RDSS', 'MuleKick / pauta de otro negocio', 'No', 'media', 'No FP', 'En agosto Mario lo marcó como No FP')
r(r'facebook|meta ads|pauta', 'BS', 'RDSS', 'Pauta FB', 'Sí', 'alta', 'Operativos')
r(r'jorge maxx|audiences', 'B', 'RDSS', 'Generación de contenido', 'Sí', 'alta', 'Operativos')
r(r'jorge (arturo )?lee', 'B', 'RDSS', 'Iguala', 'Sí', 'alta', 'Operativos')
# --- POS ---
r(r'poster|strsoftware', 'BS', 'Fijos', 'POS', 'Sí', 'alta', 'Servicios')
# --- Renta y traspasos internos ---
r(r'apartado.*renta|monto apartado', 'B', 'Traspaso', 'Apartado de renta (movimiento interno)', 'No', 'alta', 'No FP', 'Mario: no es gasto, es apartado a la cuenta de renta')
r(r'\brags?26\b|renta brisas', 'B', 'Fijos', 'Renta', 'Sí', 'alta', 'Servicios')
# --- Gasolina / viáticos ---
r(r'gasol|estacion|servifacil|picachos', 'BS', 'Variables', 'Viáticos / gasolina', 'Sí', 'media', 'Operativos')
# --- Servicios SMA ---
r(r'totalplay|megacable|organismo operador|servicio de agua|\bcfe\b|\bgas\b', 'S', 'Fijos', 'Servicios (internet, agua, luz, gas)', 'Sí', 'media', 'Servicios')
# --- SMA: nómina conocida (tabla SMA de Mario) ---
r(r'raquel murillo|darel|frias corona|saul|chava|sr eli|salvador hernandez|juan gerardo serna|carlos gaxiola|jessica (gabriela )?ariz|gerardo\b|zoe mariel|viridiana', 'S', 'Fijos', 'Nómina', 'Sí', 'media', 'Nómina', 'Nombre de persona; confirmar que es nómina SMA')
# --- SMA: insumos ---
r(r'costco|sam.?s club|toyo|alcatraces|pedido aldama|rappi|la comer|mr pechan|taqueria|barbacoa|carnitas|oxxo', 'S', 'Insumos', 'Insumos / compras', 'Sí', 'baja', 'Sin clasificar', 'Compra de comercio: puede ser insumo o consumo personal')
# --- Personal / no FP (apelan a lo que Mario marcó como Gasto personal) ---
r(r'andrea sanchez|ilce otamendi|enrique carrillo|cinemex|netflix|spotify|miniso|decathlon|starbucks|liverpool|amazon|office depot|coursera|adobe|openai|chatgpt|google|canva|apple|reto actinver|actinver|telcel|marioart|tarjeta de credito|\btdc\b|melissa gail', 'S', 'Gasto personal', 'Personal / otro negocio', 'No', 'media', 'No FP', 'Parecido a lo que Mario marcó como gasto personal en agosto')
# --- Préstamos grandes SMA ---
r(r'prestamo', 'S', 'Préstamo', 'Préstamo (movimiento financiero)', 'No', 'media', 'Préstamos')
# --- Comisión bancaria ---
r(r'comisi', 'BS', 'Comisión bancaria', 'Comisión bancaria', 'Sí', 'alta', 'Comisiones')

def classify(x):
    txt = f"{x.get('sub','')} {x.get('con','')}"
    for rx, br, cat, trat, fp, conf, bucket, nota in R:
        if x['b'] in br and rx.search(txt):
            return dict(cat=cat, trat=trat, fp=fp, conf=conf, bucket=bucket, nota=nota, regla=rx.pattern[:40])
    if re.search(r'retiro (en )?(cajero|ventanilla|efectivo)', txt, re.I):
        return dict(cat='Por revisar', trat='Retiro en efectivo', fp='Revisar', conf='baja', bucket='Sin clasificar', nota='Mario: confirmar a dónde fue el efectivo', regla='retiro')
    return dict(cat='Por revisar', trat='', fp='Revisar', conf='baja', bucket='Sin clasificar', nota='Sin regla', regla='')
