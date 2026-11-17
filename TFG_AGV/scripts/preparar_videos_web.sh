#!/bin/sh
# Genera las versiones ligeras de los vídeos explicativos para la app móvil y sus portadas.
#   videos_explicativos/web/*.mp4      720p, 30 fps, sin audio, H.264 con faststart (~2 MB cada uno)
#   videos_explicativos/portadas/*.jpg fotograma del segundo 12, para miniaturas y póster
# Los originales no se tocan: los usan la app de escritorio, los tests y «Probar con el vídeo de ejemplo».
# Uso (desde TFG_AGV/): sh scripts/preparar_videos_web.sh
set -e
cd "$(dirname "$0")/../videos_explicativos"
mkdir -p web portadas
for f in v_e_*.mp4; do
  b=${f%.mp4}
  ffmpeg -v error -y -i "$f" -an -vf "scale=720:-2,fps=30,eq=contrast=1.04:saturation=1.08" \
    -c:v libx264 -preset slow -crf 27 -profile:v high -pix_fmt yuv420p -movflags +faststart "web/$b.mp4"
  ffmpeg -v error -y -ss 12 -i "$f" -frames:v 1 -vf "scale=540:-2,eq=contrast=1.04:saturation=1.08" -q:v 4 "portadas/$b.jpg"
  echo "$b listo"
done
