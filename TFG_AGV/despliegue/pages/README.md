# Demo pública en GitHub Pages

https://telerehabia.iaencrudo.es (repositorio `agomezve/telerehab-demo`)

Es la misma app web, sin servidor y solo con pacientes **ficticios** (Carmen, Julian, Lucia):

- `demo.js` se carga antes que `app.js` y responde a `fetch("/api/...")` con las respuestas
  capturadas del servidor real. Lo que se cambia en la demo se guarda solo en ese navegador.
- La serie «en directo» reproduce una serie ya analizada por el motor real (MediaPipe) sobre el
  vídeo de ejemplo. La cámara en directo necesita el servidor.
- Las fechas se desplazan para que la demo parezca siempre de hoy.

## Regenerarla (desde `TFG_AGV/`)

```sh
TFG/bin/python despliegue/pages/grabar_series_demo.py ~/.cache/telerehab-demo          # ~5 min
TFG/bin/python despliegue/pages/construir_demo.py ~/.cache/telerehab-demo ../../telerehab-demo
cd ../../telerehab-demo && git add -A && git commit -m "Actualizar demo" && git push
```

DNS en DonDominio: CNAME `telerehabia` → `agomezve.github.io.`
