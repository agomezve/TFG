"""Extrae (una sola vez) los landmarks de MediaPipe de los vídeos de muestra
y los guarda en tests/fixtures/*.npz para que los tests sean rápidos y deterministas.

Uso:  python tests/extraer_landmarks.py
"""
import glob
import os
import sys

import cv2
import mediapipe as mp
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "tests", "fixtures")


def extraer(ruta_video):
    pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1,
                                  min_detection_confidence=0.5, min_tracking_confidence=0.5)
    cap = cv2.VideoCapture(ruta_video)
    mundo, imagen = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if res.pose_world_landmarks and res.pose_landmarks:
            mundo.append([[l.x, l.y, l.z, l.visibility] for l in res.pose_world_landmarks.landmark])
            imagen.append([[l.x, l.y, l.z, l.visibility] for l in res.pose_landmarks.landmark])
    cap.release()
    pose.close()
    return np.array(mundo, dtype=np.float32), np.array(imagen, dtype=np.float32)


if __name__ == "__main__":
    os.makedirs(DESTINO, exist_ok=True)
    videos = sorted(glob.glob(os.path.join(RAIZ, "videos", "*", "*.mp4")))
    for v in videos:
        nombre = os.path.basename(os.path.dirname(v)) + "__" + os.path.splitext(os.path.basename(v))[0].replace(" ", "_")
        mundo, imagen = extraer(v)
        np.savez_compressed(os.path.join(DESTINO, nombre + ".npz"), mundo=mundo, imagen=imagen)
        print(f"{nombre}: {len(mundo)} frames con persona detectada")
    sys.exit(0)
