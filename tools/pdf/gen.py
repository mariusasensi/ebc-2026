# Genera els dos PDFs del trek (A4 i 16:9) amb mapes OSM + GPX i estil "Expedició 1953".
# Ús: python3 tools/pdf/gen.py   (només Python 3 i Google Chrome; CHROME=/ruta/al/chrome si no és al lloc habitual)
# Dades: index.html (DATA) + gpx/ + times.json (horaris de cada dia). Sortida: pdf/*.pdf
import json, math, re, sys, os, html, time, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..", "..")
_line = next(l for l in open(os.path.join(REPO, "index.html")) if l.startswith("const DATA = "))
D = json.loads(_line[len("const DATA = "):].rstrip().rstrip(";"))
TIMES = {int(k): v for k, v in json.load(open(os.path.join(HERE, "times.json"))).items()}
S = D["stages"]
PEAKS = [["Everest", 8849, 27.9881, 86.9250], ["Lhotse", 8516, 27.9617, 86.9333], ["Nuptse", 7861, 27.9670, 86.8860],
         ["Pumori", 7161, 28.0147, 86.8286], ["Ama Dablam", 6812, 27.8617, 86.8613], ["Thamserku", 6623, 27.7867, 86.7914],
         ["Kala Patthar", 5644, 27.9958, 86.8285]]
MONTHS = ["", "gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost", "setembre", "octubre", "novembre", "desembre"]
DOW = ["dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"]
FLAGS = ["#4C6A86", "#F3EBD8", "#9C3A2C", "#5D7550", "#C9A54A"]   # blau, blanc, vermell, verd, groc (tema 1953)
NEED = set()

def nf(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def gpx(path):
    t = open(os.path.join(REPO, path)).read()
    pts = [(float(a), float(b), float(c)) for a, b, c in
           re.findall(r'<trkpt lat="([-\d.]+)" lon="([-\d.]+)">\s*<ele>([-\d.]+)</ele>', t)]
    return pts

def hav(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

TR = [gpx(s["gpx"]) for s in S]

def thin(pts, n):
    step = max(1, len(pts) // n)
    return pts[::step] + [pts[-1]]

# ---------- mapes ----------
def wpx(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def tmap(W, H, focus, others=(), pins=(), peaks=False, pad=36, labels=()):
    """Mapa W×H px: tessel·les OSM + traçat. focus/others: llistes de punts (lat, lon, ...)."""
    allp = [p for tr in focus for p in tr]
    la = [p[0] for p in allp]; lo = [p[1] for p in allp]
    x0, y0 = wpx(max(la), min(lo), 0); x1, y1 = wpx(min(la), max(lo), 0)
    f = min(math.log2((W - 2 * pad) / max(x1 - x0, 1e-9)), math.log2((H - 2 * pad) / max(y1 - y0, 1e-9)), 16.5)
    zt = min(17, math.ceil(f - 0.3))          # ponytail: tessel·les a ~1x (96 ppp); més nitidesa = més tessel·les
    s = 2 ** (f - zt)
    cx, cy = wpx((max(la) + min(la)) / 2, (max(lo) + min(lo)) / 2, zt)
    ox, oy = cx - W / 2 / s, cy - H / 2 / s
    out = [f'<div class="map" style="width:{W}px;height:{H}px">']
    for ty in range(int(oy // 256), int((oy + H / s) // 256) + 1):
        for tx in range(int(ox // 256), int((ox + W / s) // 256) + 1):
            NEED.add((zt, tx, ty))
            out.append(f'<img src="../tiles/{zt}/{tx}/{ty}.png" style="left:{(tx*256-ox)*s:.1f}px;top:{(ty*256-oy)*s:.1f}px;width:{256*s+.6:.1f}px">')
    P = lambda la, lo: tuple(round(v, 1) for v in ((wpx(la, lo, zt)[0] - ox) * s, (wpx(la, lo, zt)[1] - oy) * s))
    path = lambda tr: "M" + " L".join("%s %s" % P(p[0], p[1]) for p in thin(tr, 900))
    svg = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for tr in others:
        svg.append(f'<path d="{path(tr)}" class="t-oth"/>')
    for tr in focus:
        d = path(tr)
        svg.append(f'<path d="{d}" class="t-cas"/><path d="{d}" class="t-main"/>')
    if peaks:
        for n, a, pla, plo in PEAKS:
            x, y = P(pla, plo)
            if 8 < x < W - 8 and 8 < y < H - 8:
                left = x > W - 120 or n == "Kala Patthar"   # a l'esquerra si no hi cap o si topa amb l'estrella de l'EBC
                tx, anc = (x - 8, "end") if left else (x + 8, "start")
                svg.append(f'<path d="M{x} {y-6} l6 10 h-12z" class="pk"/><text x="{tx}" y="{y+4}" text-anchor="{anc}" class="pkt">{n} <tspan>{nf(a)}</tspan></text>')
    for (pla, plo, cls) in pins:
        x, y = P(pla, plo)
        if cls == "ebc":
            svg.append(f'<text x="{x}" y="{y+7}" class="star">★</text>')
        else:
            svg.append(f'<circle cx="{x}" cy="{y}" r="{6 if cls=="a" else 5}" class="pin {cls}"/>')
    for (pla, plo, txt) in labels:
        x, y = P(pla, plo)
        svg.append(f'<text x="{x+9}" y="{y+4}" class="lbl">{html.escape(txt)}</text>')
    svg.append("</svg>")
    out += svg
    out.append('<span class="attr">© OpenStreetMap contributors</span></div>')
    return "".join(out)

# ---------- perfils ----------
def prof_data(tr):
    xs, d = [0.0], 0.0
    for a, b in zip(tr, tr[1:]):
        d += hav(a, b); xs.append(d)
    return list(zip(xs, [p[2] for p in tr]))

def profile(W, H, segs, hi=None, marks=()):
    """segs: llista de perfils [(km, ele)] concatenats; hi: índex del segment destacat."""
    pts, off, bounds = [], 0.0, []
    for sg in segs:
        sg = thin(sg, 1200 // max(1, len(segs)) + 60)
        pts.append([(off + k, e) for k, e in sg]); bounds.append((off, off + sg[-1][0])); off += sg[-1][0]
    allp = [p for sg in pts for p in sg]
    emin = math.floor(min(e for _, e in allp) / 500) * 500; emax = math.ceil(max(e for _, e in allp) / 500) * 500
    L, R, T, B = 44, 10, 10, 22
    X = lambda k: L + k / off * (W - L - R)
    Y = lambda e: T + (emax - e) / (emax - emin) * (H - T - B)
    o = [f'<svg class="prof" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for e in range(emin, emax + 1, 500):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(e):.1f}" y2="{Y(e):.1f}" class="grid"/><text x="{L-6}" y="{Y(e)+3:.1f}" class="ax" text-anchor="end">{nf(e)}</text>')
    step = 1 if off < 14 else 10 if off < 80 else 20
    k = 0
    while k <= off + 1e-6:
        o.append(f'<text x="{X(k):.1f}" y="{H-6}" class="ax" text-anchor="middle">{k:g} km</text>'); k += step
    for i, sg in enumerate(pts):
        d = "M%.1f %.1f " % (X(sg[0][0]), Y(emin)) + " ".join("L%.1f %.1f" % (X(k), Y(e)) for k, e in sg) + " L%.1f %.1f Z" % (X(sg[-1][0]), Y(emin))
        cls = "a-hi" if hi == i else "a-dim" if hi is not None else "a"
        o.append(f'<path d="{d}" class="{cls}"/>')
    line = " ".join(("M" if j == 0 else "L") + "%.1f %.1f" % (X(k), Y(e)) for j, (k, e) in enumerate(allp))
    o.append(f'<path d="{line}" class="ln"/>')
    if len(segs) > 1:
        for i, (a, b) in enumerate(bounds):
            if i: o.append(f'<line x1="{X(a):.1f}" x2="{X(a):.1f}" y1="{T}" y2="{H-B}" class="sep"/>')
            o.append(f'<text x="{X((a+b)/2):.1f}" y="{T+12}" class="dn" text-anchor="middle">{i+1}</text>')
    for k, e, txt in marks:
        o.append(f'<text x="{X(k):.1f}" y="{Y(e)-6:.1f}" class="star" text-anchor="middle">★</text><text x="{X(k)+8:.1f}" y="{Y(e)-10:.1f}" class="mk">{txt}</text>')
    o.append("</svg>")
    return "".join(o)

def accl(W, H):
    L, R, T, B = 44, 12, 14, 26
    lo, hi = 2500, 5500
    X = lambda d: L + (d - 0.5) / 13 * (W - L - R)
    Y = lambda e: T + (hi - e) / (hi - lo) * (H - T - B)
    o = [f'<svg class="prof" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    for e in range(lo, hi + 1, 500):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(e):.1f}" y2="{Y(e):.1f}" class="grid"/><text x="{L-6}" y="{Y(e)+3:.1f}" class="ax" text-anchor="end">{nf(e)}</text>')
    bw = (W - L - R) / 13 * .5
    for s in S:
        x = X(s["day"])
        o.append(f'<rect x="{x-bw/2:.1f}" y="{Y(s["max"]):.1f}" width="{bw:.1f}" height="{Y(lo)-Y(s["max"]):.1f}" class="bar{" ebc" if s["day"]==8 else ""}"/>')
        o.append(f'<text x="{x:.1f}" y="{H-8}" class="ax" text-anchor="middle">{s["day"]}</text>')
    sl = " ".join(("M" if i == 0 else "L") + "%.1f %.1f" % (X(s["day"]), Y(s["sleepAlt"])) for i, s in enumerate(S))
    o.append(f'<path d="{sl}" class="sleep"/>')
    for s in S:
        o.append(f'<rect x="{X(s["day"])-3.5:.1f}" y="{Y(s["sleepAlt"])-3.5:.1f}" width="7" height="7" class="sq"/>')
    o.append("</svg>")
    return "".join(o)

# ---------- textos ----------
def route(s, alts=True):
    if s["kind"] == "accl6": return "Aclimatació per Dingboche fins als 4.800 m"
    names = [f"{n} ({nf(a)} m)" if alts and a else n for n, a in s["route"]]
    if s["kind"] == "accl": return "Aclimatació: " + " → ".join(n for n, _ in s["route"])
    return " → ".join(names)

def longdate(s):
    import datetime
    d, m, y = map(int, s["date"].split("/"))
    return f"{DOW[datetime.date(y, m, d).weekday()].capitalize()}, {d} de {MONTHS[m]} de {y}"

def tag(s):
    return "Aclimatació" if s["kind"] in ("accl", "accl6") else "Everest Base Camp" if s["day"] == 8 else ""

def flag(s, big=False):
    c = FLAGS[(s["day"] - 1) % 5]
    fg = "#2B2118" if c in ("#F3EBD8", "#C9A54A") else "#F6EEDB"
    return f'<span class="flag{" big" if big else ""}" style="background:{c};color:{fg}">{s["day"]}</span>'

TOT_KM = sum(s["km"] for s in S); TOT_UP = sum(s["up"] for s in S); TOT_DN = sum(s["dn"] for s in S)
def hm(txt): h, m = map(int, re.findall(r"\d+", txt)); return h * 60 + m
def fmt(mins): return f"{mins // 60} h {mins % 60:02d}"
TOT_MOV = fmt(sum(hm(TIMES[s["day"]]["mov"]) for s in S)); TOT_TOT = fmt(sum(hm(TIMES[s["day"]]["total"]) for s in S))
PROFS = [prof_data(tr) for tr in TR]

def stat(v, u, l): return f'<div class="st"><b>{v}<small>{u}</small></b><span>{l}</span></div>'

def kpis():
    return (stat(13, "", "dies") + stat(nf(TOT_KM, 1), "km", "distància") + stat(nf(TOT_UP), "m", "desnivell positiu")
            + stat(nf(5364), "m", "Everest Base Camp") + stat(TOT_MOV.replace(" ", " "), "", "en moviment"))

def day_stats(s):
    t = TIMES[s["day"]]
    a = (stat(nf(s["km"], 2), "km", "distància") + stat(nf(s["up"]), "m", "desnivell +") + stat(nf(s["dn"]), "m", "desnivell −")
         + stat(nf(s["max"]), "m", "altitud màxima") + stat(t["mov"].replace(" ", " "), "", "en moviment"))
    b = "".join(f'<div><span>{k}</span><b>{v}</b></div>' for k, v in
                [("Alt. mínima", t["minAlt"]), ("Inici", t["start"]), ("Final", t["end"]), ("Temps total", t["total"]),
                 ("Aturats", t["stopped"]), ("Vel. mitjana", t["speed"])])
    return f'<div class="kpis">{a}</div><div class="log">{b}</div>'

def night(s):
    return f"Final del trek a Lukla ({nf(s['sleepAlt'])} m)." if s["day"] == 13 else f"Nit a {s['sleep']} ({nf(s['sleepAlt'])} m)."

def table(compact=False):
    rows = []
    for s in S:
        t = TIMES[s["day"]]
        rows.append(f'<tr><td>{flag(s)}</td><td class="dt">{s["date"][:5]}</td><td class="rt">{route(s)}</td><td>{nf(s["km"],2)}</td>'
                    f'<td>{nf(s["up"])}</td><td>{nf(s["dn"])}</td><td>{nf(s["max"])}</td><td>{t["mov"]}</td><td>{t["total"]}</td></tr>')
    return ('<table class="tbl"><thead><tr><th></th><th>Data</th><th>Etapa</th><th>km</th><th>D+</th><th>D−</th><th>Alt. màx.</th><th>Mov.</th><th>Total</th></tr></thead><tbody>'
            + "".join(rows) + f'</tbody><tfoot><tr><td></td><td></td><td>Total</td><td>{nf(TOT_KM,2)}</td><td>{nf(TOT_UP)}</td><td>{nf(TOT_DN)}</td><td></td><td>{TOT_MOV}</td><td>{TOT_TOT}</td></tr></tfoot></table>')

def records():
    lng = max(S, key=lambda s: s["km"]); up = max(S, key=lambda s: s["up"]); dn = max(S, key=lambda s: s["dn"])
    lt = max(S, key=lambda s: hm(TIMES[s["day"]]["total"]))
    r = [("Etapa més llarga", f'Dia {lng["day"]} · {nf(lng["km"],2)} km'), ("Més desnivell positiu", f'Dia {up["day"]} · {nf(up["up"])} m'),
         ("Més desnivell negatiu", f'Dia {dn["day"]} · {nf(dn["dn"])} m'), ("Jornada més llarga", f'Dia {lt["day"]} · {TIMES[lt["day"]]["total"]}')]
    return '<div class="rec"><h3>Rècords</h3>' + "".join(f'<div><span>{a}</span><b>{b}</b></div>' for a, b in r) + "</div>"

def pins_for(i):
    tr = TR[i]; a, z = tr[0], tr[-1]
    pins = [(a[0], a[1], "a")]
    if hav(a, z) > 0.15: pins.append((z[0], z[1], "b"))
    if S[i]["day"] == 8: pins.append((D["ebc"][0], D["ebc"][1], "ebc"))
    return pins

def sleep_labels():
    lab, seen = [], set()
    for s, tr in zip(S, TR):
        if s["sleep"] not in seen:
            seen.add(s["sleep"]); lab.append((tr[-1][0], tr[-1][1], s["sleep"]))
    return lab

def ebc_mark(whole):
    # l'EBC és el punt més alt del dia 8; al perfil global, desplaçat pels 7 dies anteriors
    k, e = max(PROFS[7], key=lambda p: p[1])
    off = sum(PROFS[j][-1][0] for j in range(7)) if whole else 0
    return [(off + k, e, "EBC 5.364 m")]

# ---------- pàgines ----------
def head(cls, title):
    css = open(os.path.join(HERE, "style.css")).read()
    css += "@page { size: %s; margin: 0; }" % ("210mm 297mm" if cls == "a4" else "960pt 540pt")
    return (f'<!doctype html><html lang="ca"><head><meta charset="utf-8"><title>{title}</title>'
            '<link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Special+Elite&display=swap" rel="stylesheet">'
            f'<style>{css}</style></head><body class="{cls}">')

def foot(n, total):
    return f'<div class="pfoot"><span>Expedició al Camp Base de l’Everest · novembre 2026</span><span>{n} / {total}</span></div>'

def a4():
    P, N = [], 15
    allx = [TR]
    P.append(f'''<section class="page cover">
      <div class="kicker">Informe de l’expedició · Nepal · Vall del Khumbu</div>
      <h1>Trekking al Camp Base<br>de l’Everest</h1>
      <p class="sub">Del 4 al 16 de novembre de 2026 · a peu des de Lukla pel Parc Nacional de Sagarmatha</p>
      <div class="kpis">{kpis()}</div>
      <div class="frame">{tmap(714, 520, TR, pins=[(D["lukla"][0], D["lukla"][1], "a"), (D["ebc"][0], D["ebc"][1], "ebc")], peaks=True, labels=sleep_labels())}</div>
      <h3>Perfil del recorregut</h3>
      <div class="frame pf">{profile(714, 150, PROFS, marks=ebc_mark(True))}</div>
      {foot(1, N)}</section>''')
    P.append(f'''<section class="page">
      <h2>Les etapes</h2>
      {table()}
      <h2 class="mt">Aclimatació</h2>
      <p class="cap">Altitud on vam dormir cada nit (línia) i màxima assolida cada dia (barres).</p>
      <div class="frame pf">{accl(714, 240)}</div>
      {foot(2, N)}</section>''')
    for i, s in enumerate(S):
        others = [tr for j, tr in enumerate(TR) if j != i]
        tg = tag(s)
        P.append(f'''<section class="page day">
          <div class="dhead">{flag(s, True)}<div><div class="kicker">Dia {s["day"]} · {longdate(s)}{f" · <em>{tg}</em>" if tg else ""}</div>
          <h2>{route(s)}</h2></div></div>
          {day_stats(s)}
          <div class="frame">{tmap(714, 470, [TR[i]], others, pins_for(i))}</div>
          <h3>Perfil d’elevació</h3>
          <div class="frame pf">{profile(714, 150, [PROFS[i]], marks=ebc_mark(False) if s["day"]==8 else ())}</div>
          <p class="night">{night(s)}</p>
          {foot(i + 3, N)}</section>''')
    return head("a4", "Trekking al Camp Base de l’Everest") + "".join(P) + "</body></html>"

def deck():
    P, N = [], 16
    P.append(f'''<section class="slide cover">
      <div class="col">
        <div class="kicker">Informe de l’expedició · Nepal · Vall del Khumbu</div>
        <h1>Trekking al Camp Base<br>de l’Everest</h1>
        <p class="sub">4–16 de novembre de 2026</p>
        <div class="kpis k2">{stat(13,"","dies")}{stat(nf(TOT_KM,1),"km","distància")}{stat(nf(TOT_UP),"m","desnivell positiu")}{stat(nf(TOT_DN),"m","desnivell negatiu")}{stat(nf(5364),"m","Everest Base Camp")}{stat(TOT_MOV.replace(" "," "),"","en moviment")}</div>
        {records()}
      </div>
      <div class="frame">{tmap(520, 600, TR, pins=[(D["lukla"][0], D["lukla"][1], "a"), (D["ebc"][0], D["ebc"][1], "ebc")], peaks=True, labels=sleep_labels())}</div>
      {foot(1, N)}</section>''')
    P.append(f'''<section class="slide stack">
      <h2>Perfil del recorregut</h2>
      <div class="frame pf">{profile(1200, 250, PROFS, marks=ebc_mark(True))}</div>
      <h2 class="mt">Aclimatació</h2>
      <p class="cap">Altitud on vam dormir cada nit (línia) i màxima assolida cada dia (barres).</p>
      <div class="frame pf">{accl(1200, 210)}</div>
      {foot(2, N)}</section>''')
    P.append(f'''<section class="slide stack"><h2>Les etapes</h2>{table()}{foot(3, N)}</section>''')
    for i, s in enumerate(S):
        others = [tr for j, tr in enumerate(TR) if j != i]
        tg = tag(s)
        P.append(f'''<section class="slide day">
          <div class="col">
            <div class="dhead">{flag(s, True)}<div><div class="kicker">Dia {s["day"]} · {longdate(s)}{f" · <em>{tg}</em>" if tg else ""}</div>
            <h2>{route(s)}</h2></div></div>
            {day_stats(s)}
            <h3>Perfil d’elevació</h3>
            <div class="frame pf">{profile(600, 250, [PROFS[i]], marks=ebc_mark(False) if s["day"]==8 else ())}</div>
            <p class="night">{night(s)}</p>
          </div>
          <div class="frame">{tmap(520, 600, [TR[i]], others, pins_for(i))}</div>
          {foot(i + 4, N)}</section>''')
    return head("deck", "Trekking al Camp Base de l’Everest · presentació") + "".join(P) + "</body></html>"

def fetch_tiles():
    # Només les que falten, a poc a poc i identificant-nos (política d'ús de tile.openstreetmap.org)
    for z, x, y in sorted(NEED):
        f = os.path.join(HERE, "tiles", str(z), str(x), f"{y}.png")
        if os.path.exists(f): continue
        os.makedirs(os.path.dirname(f), exist_ok=True)
        req = urllib.request.Request(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png", headers={
            "User-Agent": "ebc-2026-trip-report/1.0 (+https://github.com/mariusasensi/ebc-2026)",
            "Referer": "https://mariusasensi.github.io/ebc-2026/"})
        open(f, "wb").write(urllib.request.urlopen(req, timeout=30).read())
        time.sleep(.25)

if __name__ == "__main__":
    docs = {"Trekking_EBC_Nepal_2026": a4(), "Trekking_EBC_Nepal_2026_16x9": deck()}
    fetch_tiles()
    chrome = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    for name, doc in docs.items():
        page = os.path.join(HERE, "out", name + ".html")
        open(page, "w").write(doc)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                        f"--user-data-dir={os.path.join(HERE, 'out', 'chrome')}",
                        f"--print-to-pdf={os.path.join(REPO, 'pdf', name + '.pdf')}", "file://" + page],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("pdf/" + name + ".pdf")
