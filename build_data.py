#!/usr/bin/env python3
"""Funky Panda - genera data por audiencia y los 3 dashboards (mario / brisas / socios).
Lee raw/*.json (volcados de Airtable). Si hay AIRTABLE_TOKEN, vuelve a bajar los datos primero.
Uso: python3 build_data.py        -> mario.html brisas.html socios.html
"""
import json, base64, os, re, glob, datetime as dt, collections
import clasif

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
BASE = 'appvDywRWEiRY5oPP'
TABLES = {'ventas': 'tblHw4y5D5GGuneVi', 'canal': 'tblCuKQAOfbRWniWb', 'gastos': 'tblZB1hjuPZigOIYB', 'cierres': 'tblW7aO1M5uSZwxUy'}

HUELLA = []                  # resumen sin datos (modo, llamadas, huella por dashboard) -> huella.txt
INCR = ('canal', 'gastos')   # tablas grandes: solo se bajan los registros nuevos/editados y se juntan con la copia guardada (raw.enc)
FULL_DAYS = 7                 # cada 7 días se baja todo completo (atrapa borrados y campos calculados)

def _fetch(tok, tid, formula=None):
    import urllib.request, urllib.parse
    recs_, off, calls = [], None, 0
    while True:
        q = {'returnFieldsByFieldId': 'true', 'pageSize': '100'}
        if formula: q['filterByFormula'] = formula
        if off: q['offset'] = off
        url = f'https://api.airtable.com/v0/{BASE}/{tid}?' + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + tok})
        d = json.load(urllib.request.urlopen(req)); calls += 1
        recs_ += [{'id': r['id'], 'cellValuesByFieldId': r['fields']} for r in d['records']]
        off = d.get('offset')
        if not off: return recs_, calls

def _load_cache():
    p = f'{HERE}/raw.enc'
    if not os.path.exists(p): return None
    try: return json.loads(decrypt_text(open(p).read(), get_passwords()['mario']))
    except Exception as e: print('raw.enc no se pudo leer, se baja todo:', e); return None

def refresh_from_airtable():
    tok = os.environ['AIRTABLE_TOKEN']
    os.makedirs(RAW, exist_ok=True)
    now = dt.datetime.utcnow()
    cache = _load_cache()
    full = (os.environ.get('FULL_REFRESH') == '1' or not cache or
            now - dt.datetime.fromisoformat(cache['full_at']) > dt.timedelta(days=FULL_DAYS))
    if full: cache = {'full_at': now.isoformat(), 'tables': {}}
    since = None if full else (dt.datetime.fromisoformat(cache['fetched_at']) - dt.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    total = 0
    for name, tid in list(TABLES.items()) + [('prod', 'tblk1L5P2IpkKwBtm')]:
        if name in INCR and not full:
            f = f"OR(IS_AFTER(CREATED_TIME(),'{since}'),IS_AFTER(LAST_MODIFIED_TIME(),'{since}'))"
            new, n = _fetch(tok, tid, f)
            byid = {r['id']: r for r in cache['tables'][name]}
            for r in new: byid[r['id']] = r
            recs_ = list(byid.values())
            print(f'{name}: {len(new)} nuevos/editados, {len(recs_)} total ({n} llamadas)')
        else:
            recs_, n = _fetch(tok, tid)
            print(f'{name}: {len(recs_)} completos ({n} llamadas)')
        total += n
        if name in INCR: cache['tables'][name] = recs_
        if name == 'prod':
            for f_ in glob.glob(f'{RAW}/prod*.json'): os.remove(f_)
            for i in range(0, len(recs_), 50):
                json.dump({'records': recs_[i:i+50]}, open(f'{RAW}/prod{i // 50 + 1}.json', 'w'))
        else:
            json.dump({'records': recs_}, open(f'{RAW}/{name}.json', 'w'))
    cache['fetched_at'] = now.isoformat()
    open(f'{HERE}/raw.enc', 'w').write(encrypt_html(json.dumps(cache, separators=(',', ':')), get_passwords()['mario']))
    print('Airtable:', 'COMPLETO' if full else 'incremental', '-', total, 'llamadas')
    HUELLA.append(f"{now:%Y-%m-%d %H:%M}Z {'COMPLETO' if full else 'incremental'} {total} llamadas")

def recs(f):
    d = json.load(open(f))
    return d['records'] if isinstance(d, dict) else d

# ---------- categorias Poster ----------
CAT = {1: 'Asiática', 2: 'Mexicana', 3: 'Postres', 4: 'Bebidas', 6: 'Extras', 7: 'Pa Niños', 8: 'Sushi', 9: 'Mule Kick',
       10: 'Especiales', 12: 'Destilados', 13: 'Vino', 14: 'Entradas', 18: 'Cerveza', 27: 'Chupe/Tragos', 28: 'Pizza', 29: 'Café'}
BEBIDA_IDS = {4, 18, 13, 12, 29, 27}
GRUPO = {1: 'Asiática', 14: 'Asiática', 2: 'Mexicana', 8: 'Sushi', 9: 'Mule Kick', 28: 'Pizza',
         4: 'Bebidas sin alcohol', 29: 'Bebidas sin alcohol',
         18: 'Alcohol', 13: 'Alcohol', 12: 'Alcohol', 27: 'Alcohol'}
GRUPOS = ['Asiática', 'Mexicana', 'Sushi', 'Mule Kick', 'Pizza', 'Bebidas sin alcohol', 'Alcohol', 'Otros']

def build():
    B = {'recy00b9ljOGOYmjp': 'B', 'reczTspzmqfMf510m': 'S'}
    daily = []
    for r in recs(f'{RAW}/ventas.json'):
        c = r['cellValuesByFieldId']
        s = 'B' if c['fldI7kSA6NF2mCBOT'].endswith('Brisas') else 'S'
        g = lambda k: round(c.get(k) or 0, 2)
        daily.append(dict(d=c['fldatJACI7EDhrgoX'], b=s, rec=int(c.get('flddZAIvFnhuLJYH3') or 0), ef=g('fldX2HbnhNuA8ZmF4'),
                          tj=g('fldmtG2SsLQXgk58N'), ub=g('fldiYH6rhQJKKBav9'), rp=g('fldT7VV4xvx7QPTM9'), cl=g('fldunW2LCXdpGAqK6'),
                          mp=g('fld2s6mBr3Y0BiEKS'), pw=g('fldGqUBlPBKwbrBCY'), prop=g('fld2PkKbSpb7vETUc'),
                          desc=g('fldP8jLp9GTcfa6tw'), ing=g('fldbTypmyvl90151G')))
    daily.sort(key=lambda x: (x['d'], x['b']))
    canal = []
    for r in recs(f'{RAW}/canal.json'):
        c = r['cellValuesByFieldId']
        ch = c.get('fld9zmknKmc7Jb2uJ')
        if ch not in ('Salón', 'Para llevar', 'Reparto', 'Uber Eats'): continue
        s = c['fldF6i8x632cr0Rzj'].split('-')[1]
        canal.append(dict(d=c['fldDND2oeZCi0HKX6'], b=s, c=ch, t=int(c.get('fldOkoib3khVFTzdt') or 0), i=round(c.get('fld4ixXEHyIb5vk1I') or 0, 2)))
    canal.sort(key=lambda x: (x['d'], x['b'], x['c']))
    prod = collections.defaultdict(lambda: [0.0, 0.0])
    for f in sorted(glob.glob(f'{RAW}/prod*.json')):
        for r in recs(f):
            c = r['cellValuesByFieldId']
            k = c.get('fldHn7vUyQ6uMJGy3') or ''
            m = re.match(r'(\d{4})(\d{2})(\d{2})-([BS])$', k)
            if not m or not c.get('fldJIjKocMddYkNcJ'): continue
            d = f'{m[1]}-{m[2]}-{m[3]}'; s = m[4]
            try: items = json.loads(base64.b64decode(c['fldJIjKocMddYkNcJ']))['response']
            except Exception: continue
            for it in items:
                name = (it.get('product_name') or '').strip()
                if name.upper() == 'ENVIO': continue
                try: cid = int(it.get('category_id'))
                except Exception: continue
                q = float(it.get('count') or 0); sm = float(it.get('payed_sum') or 0) / 100
                kk = (d, s, name, cid)
                prod[kk][0] += q; prod[kk][1] += sm
    prods = [dict(d=k[0], b=k[1], n=k[2], cid=k[3], q=round(v[0], 2), s=round(v[1], 2)) for k, v in sorted(prod.items())]
    gastos = []
    for r in recs(f'{RAW}/gastos.json'):
        c = r['cellValuesByFieldId']
        suc = c.get('fldlY7OadmDx75fM2') or []
        sid = (suc[0]['id'] if isinstance(suc[0], dict) else suc[0]) if suc else None
        s = B.get(sid, 'B')
        o = c.get('fld5cnQeotZLzy7MM'); o = o['name'] if isinstance(o, dict) else (o or '')
        cat = (c.get('fldyUd5EEfW2vSgan') or '').strip()
        if cat == 'Construccion': cat = 'Construcción'
        if cat == 'Prestamos': cat = 'Préstamos'
        if cat == 'TEST_CATS' or not c.get('fld1GRP6MALIUsuoF'): continue
        gastos.append(dict(d=c['fld1GRP6MALIUsuoF'], b=s, o=o, k=(c.get('fldvHXtEs9cjV429d') or ''), cat=cat or 'Por aclarar',
                           sub=c.get('fldRHVPX1QhVTwGtq') or '', con=c.get('fldY6xoLyIAhC3EFr') or '', t=round(c.get('fldgWghtR5Rbbv9Je') or 0, 2)))
    for x in gastos:   # clasificación propuesta (aprendida de agosto) para movimientos 'Por aclarar'
        if x['cat'] == 'Por aclarar':
            c = clasif.classify(x)
            x['cl'] = c
            if c['fp'] != 'Revisar' and c['conf'] in ('alta', 'media') and c['bucket'] != 'Sin clasificar':
                x['pr'] = 1
    gastos.sort(key=lambda x: x['d'])
    cierres = []
    if os.path.exists(f'{RAW}/cierres.json'):
        for r in recs(f'{RAW}/cierres.json'):
            c = r['cellValuesByFieldId']
            if not c.get('fldPRSt2wSbo4HM5Z'): continue
            su = c.get('fld0GcRQtg9zOEO5a') or []
            sid = (su[0]['id'] if isinstance(su[0], dict) else su[0]) if su else None
            e = c.get('fld5gFwF3FrLinhnS'); e = e['name'] if isinstance(e, dict) else (e or '')
            g_ = lambda k: round(c.get(k) or 0, 2)
            cierres.append(dict(d=c['fldPRSt2wSbo4HM5Z'], b=B.get(sid, 'B'), ab=g_('fld0hvNZLEQlLXgBL'), inc=g_('fldOuOsbhsipTDqrH'), ci=g_('fldjjcZj2pCVE58Oz'),
                ef=g_('fldueAhhq3yhiqJtF'), dif=g_('fldYWqTWAAcxkr06G'), tj=g_('fld8gTMXpScjtPksI'), ub=g_('fldZZiDcZYtgawdNZ'), pc=g_('fldkO6YeQ7wSUGcu6'),
                ptj=g_('fldqvFcdx9QHhJ4Iu'), est=e, sube=g_('fldSZmP3bAC7vUN5V'), pag=g_('fld3bCgltS1yVqEQu')))
        cierres.sort(key=lambda x: (x['d'], x['b']))
    return daily, canal, prods, gastos, cierres

FIJOS = {  # tabla de Mario (13 oct 2026), mensual, sin nómina
 'B': {'Renta': 20000, 'Gas': 4500, 'Luz': 4000, 'Internet': 949, 'Agua': 1000, 'Agencia RDSS': 5500, 'Pauta RDSS': 2000,
       'Contadora': 600, 'Otros': 2000, 'Jarcería': 1000, 'Sistema operativo': 2000, 'Móvil': 400},
 'S': {'Renta': 26500, 'Gas': 4000, 'Luz': 4000, 'Internet': 900, 'Agua': 2500, 'Agencia RDSS': 5500, 'Pauta RDSS': 2000,
       'Contadora': 600, 'Otros': 2000, 'Jarcería': 1000, 'Sistema operativo (Poster)': 1000, 'Móvil': 400},
}
NOMINA_SEM = {'B': 18950, 'S': 14150}   # plantilla de Mario: 75,800 y 56,600 al mes (x4)
# Control semanal de Mario (hoja Nomina del 'Control Funky Panda Brisas 2026', columna 5-11 oct). Solo semanas ya llenadas por él.
CONTROL = {'B': {'2026-10-05': dict(inicio=50062.29, ventas=54742.60, tj=46840.60, cash=7902.0, comision=1873.62, nomina=18950.0,
    propinas=5098.0, insumos=31162.93, caja_chica=5716.0, gas=500.0, gasolina=500.0, apartado_renta=5000.0,
    total_pagos=62084.55, disponible=42720.34, resultado=-7341.95)}}
SOCIOS_GRUPO = {'Nómina': 'Nómina', 'Insumo Directo': 'Insumos', 'Insumo Indirecto': 'Insumos'}

# Metas SEMANALES de caja chica (hoja 'Caja 2026' de Mario). Clasificación propuesta por proveedor/concepto: Mario la valida.
METAS = [('Gastos caja chica', 500), ('Gas', 1000), ('Gasolina', 500), ('Verduras y Abarrotes', 4500), ('Carne', 2300), ('Mariscos', 2500),
         ('Toyo', 1600), ('Mimi', 500), ('Costco', 1800), ('Refrescos', 1000), ('Alcohol', 2500), ('Otros', 0)]
def metacat(x):
    if x['o'] != 'Efectivo': return None
    t = (x['k'] + ' ' + x['con'] + ' ' + x['cat']).upper()
    if 'CASH OUT' in t: return None
    for pat, m in [(r'GASOLINA', 'Gasolina'), (r'\bGAS\b', 'Gas'), (r'CARNIC|CARNE|POLLO', 'Carne'), (r'MARISCO', 'Mariscos'), (r'TOYO', 'Toyo'),
                   (r'MIMI', 'Mimi'), (r'COSTCO', 'Costco'), (r'COCA|REFRESC|SIDRAL|JUMEX', 'Refrescos'), (r'CHUPE|CHELA|\bRON\b|ALCOHOL|TEQUILA|VINO', 'Alcohol'),
                   (r'FRESCO|RECAUDER|VERDUR|FRUTA|BODEGA|TORTILL|CARMELO|PAN[AE]DER|PASTELER|ABARROT|WALMART|LA COMER', 'Verduras y Abarrotes'),
                   (r'OXXO|PAPELER|FERRETER|BASURA|AGUA|HIELO|\bCP\b|TIENDA|PROPINA|DANY|POSTRES', 'Gastos caja chica')]:
        if re.search(pat, t): return m
    return 'Otros'

def bucket(x):
    if x.get('pr'): return x['cl']['bucket']
    if re.search(r'comisi', x['con'] + ' ' + x['sub'], re.I): return 'Comisiones'
    c = x['cat']
    if c == 'Por aclarar': return 'Sin clasificar'
    if c in ('Personal', 'Traspaso'): return 'No FP'   # fuera del P&L: gasto personal de Mario / apartados de renta
    if c in ('Insumo Directo', 'Insumo Indirecto', 'Insumos'): return 'Insumos'
    if c == 'Nómina': return 'Nómina'
    if c == 'Servicios': return 'Servicios'
    if c == 'Construcción': return 'Inversión'
    if c == 'Préstamos': return 'Préstamos'
    return 'Operativos'

def view(daily, canal, prods, gastos, cierres, branches, level):
    f = lambda xs: [x for x in xs if x['b'] in branches]
    g = f(gastos)
    out = dict(daily=f(daily), canal=f(canal), prods=f(prods), branches=branches,
               fijos={b: FIJOS[b] for b in branches}, nomina={b: NOMINA_SEM[b] for b in branches}, level=level, hist=[h for h in load_hist() if h['b'] in branches or (h['b'] == 'T' and 'S' in branches)],
               cierres=[x for x in cierres if x['b'] in branches] if level == 'full' else [], metas=METAS,
               control={b: CONTROL.get(b, {}) for b in branches} if level == 'full' else {})
    if level == 'socios':
        out['gastos'] = [dict(d=x['d'], b=x['b'], bk=bucket(x), pr=x.get('pr', 0), t=x['t']) for x in g]
        out['fijos'] = {b: {'Gastos operativos fijos': sum(FIJOS[b].values())} for b in branches}
    else:
        out['gastos'] = [dict(d=x['d'], b=x['b'], o=x['o'], k=x['k'], cat=x['cat'], sub=x['sub'], con=x['con'], bk=bucket(x), mc=metacat(x), pr=x.get('pr', 0), fp=(x['cl']['fp'] if x.get('pr') else ''), t=x['t']) for x in g]
    return out

def encrypt_html(html, password):
    # AES-256-GCM, clave por PBKDF2-SHA256 (200k). Formato: base64(salt16 | iv12 | cifrado+tag) del HTML comprimido con gzip.
    import gzip, secrets
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000).derive(password.encode())
    ct = AESGCM(key).encrypt(iv, gzip.compress(html.encode('utf-8'), 9), None)
    return base64.b64encode(salt + iv + ct).decode()

def decrypt_text(blob, password):
    import gzip
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    buf = base64.b64decode(blob); salt, iv, ct = buf[:16], buf[16:28], buf[28:]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000).derive(password.encode())
    return gzip.decompress(AESGCM(key).decrypt(iv, ct, None)).decode('utf-8')

def get_passwords():
    pw = {}
    pf = os.path.join(HERE, 'passwords.json')   # local, NO se sube a GitHub
    if os.path.exists(pf): pw.update(json.load(open(pf)))
    for n in ('mario', 'brisas', 'socios'):
        if os.environ.get('PW_' + n.upper()): pw[n] = os.environ['PW_' + n.upper()]
    return pw

def load_hist():
    # Base semanal de Mario (2023 a 11 oct 2026), por sucursal y semana ISO. Para semanas >= 2026-W32 manda Airtable (diario).
    p = f'{RAW}/hist.json'
    if os.path.exists(p): h = json.load(open(p))
    else:   # en GitHub el histórico vive cifrado (hist.enc) con la contraseña de Dirección
        h = json.loads(decrypt_text(open(f'{HERE}/hist.enc').read(), get_passwords()['mario']))
    return [x for x in h if not (x['b'] in ('B', 'S') and (x['y'], x['w']) >= (2026, 32))]

def main():
    if os.environ.get('AIRTABLE_TOKEN'): refresh_from_airtable()
    daily, canal, prods, gastos, cierres = build()
    last = max(x['d'] for x in daily)
    # Objetivo mensual (lo define Mario). None = por definir. ventas por sucursal (MXN/mes), insumos_pct y util_pct como fracción de ventas.
    OBJ = dict(ventas={'B': None, 'S': None}, insumos_pct=None, util_pct=None)
    meta = dict(obj=OBJ, generado=dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), ultimoCorte=last,
                cat={str(k): v for k, v in CAT.items()}, bebidas=sorted(BEBIDA_IDS),
                grupo={str(k): v for k, v in GRUPO.items()}, grupos=GRUPOS)
    tpl = open(f'{HERE}/template.html', encoding='utf-8').read()
    specs = [('mario', ['B', 'S'], 'full', 'Funky Panda · Dirección', 'Brisas + San Miguel de Allende'),
             ('brisas', ['B'], 'full', 'Funky Panda · Brisas', 'Sucursal Brisas'),
             ('socios', ['B'], 'socios', 'Funky Panda · Socios', 'Sucursal Brisas · resumen')]
    pws = get_passwords(); blobs = {}
    falta = [n for n, *_ in specs if n not in pws]
    if falta: raise SystemExit('Faltan contraseñas (PW_MARIO / PW_BRISAS / PW_SOCIOS): ' + ', '.join(falta) + '. No se publica nada sin cifrar.')
    for name, br, lvl, title, sub in specs:
        data = view(daily, canal, prods, gastos, cierres, br, lvl)
        data['meta'] = meta; data['title'] = title; data['sub'] = sub
        import hashlib; h_ = hashlib.sha256(json.dumps({k: v for k, v in data.items() if k != 'meta'}, sort_keys=True).encode()).hexdigest()[:16]; print(name, 'huella', h_); HUELLA.append(f'{name} {h_}')
        html = tpl.replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':'))).replace('__TITLE__', title)
        blobs[name] = encrypt_html(html, pws[name])
        print(name, len(html) // 1024, 'KB', 'daily', len(data['daily']), 'prods', len(data['prods']), 'gastos', len(data['gastos']))
    _write_index(blobs)
    open(f'{HERE}/huella.txt', 'w').write('\n'.join(HUELLA) + '\n')

def _write_index(blobs):
    if not blobs: return
    t = open(f'{HERE}/index_template.html', encoding='utf-8').read().replace('/*__BLOBS__*/[]', json.dumps(sorted(blobs.values())))
    open(f'{HERE}/index.html', 'w', encoding='utf-8').write(t)

if __name__ == '__main__':
    main()