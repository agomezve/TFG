# Servidor de la app móvil de TeleRehab IA, listo para la nube.
#   docker build -t telerehab .
#   docker run -p 8000:8000 -v telerehab_datos:/datos telerehab
# Los datos (BBDD, informes y vídeos) van en el volumen /datos, nunca dentro de la imagen.
FROM python:3.11-slim

# ffmpeg: convertir grabaciones a MP4 · libgl1/libglib2.0-0: necesarias para OpenCV y MediaPipe
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# customtkinter solo hace falta para la app de escritorio
RUN grep -v -i customtkinter requirements.txt > requirements-servidor.txt \
 && pip install --no-cache-dir -r requirements-servidor.txt

COPY . .

ENV TELEREHAB_DATA_DIR=/datos \
    PORT=8000 \
    PYTHONUNBUFFERED=1
VOLUME ["/datos"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/salud')" || exit 1

# Un solo proceso: las sesiones de login viven en memoria
CMD ["python", "servidor_web.py"]
