# Camp Base de l’Everest · novembre 2026

Resum del trekking de 13 dies de Lukla al Camp Base de l’Everest i tornada, amb mapa i tracks GPX per descarregar.

## Web per descarregar

El botó «Tota la web» baixa `ebc-2026-web.zip` de la release `web`. Després de canvis a la web, regenera'l:

```bash
rm -rf /tmp/ebc && mkdir -p /tmp/ebc/ebc-2026-web && cp -r index.html manifest.webmanifest sw.js og.jpg *.png gpx img pdf vendor /tmp/ebc/ebc-2026-web/
(cd /tmp/ebc/ebc-2026-web/gpx && zip -q EBC-2026-tracks.zip *.gpx) && (cd /tmp/ebc && zip -qr ebc-2026-web.zip ebc-2026-web)
gh release upload web /tmp/ebc/ebc-2026-web.zip --clobber
```
