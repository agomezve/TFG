import os
import subprocess

videos_info = [
    {
        "file": "ve_bulgaras.MOV",
        "out": "v_e_bulgaras.mp4",
        "text": "Para realizar correctamente la sentadilla búlgara, colócate de espaldas a un banco y apoya el empeine de tu pie trasero sobre él. Mantén el torso ligeramente inclinado hacia adelante para mayor activación de glúteo, o recto para enfocar el cuádriceps. Inhala mientras bajas de forma controlada hasta que el muslo delantero esté paralelo al suelo. Asegúrate de que la rodilla no colapse hacia adentro. Empuja con fuerza usando el talón delantero y exhala al subir. Mantén el abdomen contraído."
    },
    {
        "file": "ve_hip_trust.MOV",
        "out": "v_e_hip_trust.mp4",
        "text": "Para ejecutar el hip thrust de forma correcta, apoya la parte superior de tu espalda, justo debajo de las escápulas, en el borde de un banco. Coloca los pies firmes en el suelo, separados al ancho de los hombros, formando un ángulo de noventa grados en las rodillas al subir. Inhala y empuja la cadera hacia arriba contrayendo fuertemente los glúteos en la parte superior. Exhala y baja de forma controlada sin arquear la zona lumbar. Mantén la barbilla pegada al pecho."
    },
    {
        "file": "ve_plancha.MOV",
        "out": "v_e_plancha.mp4",
        "text": "Para hacer la plancha correctamente, colócate boca abajo apoyando los antebrazos y las puntas de los pies en el suelo. Tus codos deben estar justo debajo de tus hombros. Activa fuertemente el abdomen, los glúteos y los cuádriceps para mantener tu cuerpo en una línea recta y perfecta, desde la cabeza hasta los talones. No dejes que la cadera caiga ni la levantes demasiado. Respira de forma constante y profunda, sin perder la tensión del core durante todo el tiempo."
    },
    {
        "file": "ve_press_banca.MOV",
        "out": "v_e_press_banca.mp4",
        "text": "Para el press de banca correcto, acuéstate apoyando firmemente la cabeza, espalda alta y glúteos en el banco. Planta ambos pies en el suelo. Agarra la barra con una separación ligeramente superior al ancho de tus hombros. Desciende la barra de forma lenta y controlada hacia la parte media del pecho mientras inhalas. Evita rebotar la barra. Luego, exhala mientras empujas la barra hacia arriba con fuerza hasta extender casi por completo los codos, manteniendo los hombros siempre retraídos."
    },
    {
        "file": "ve_propiocepcion.MOV",
        "out": "v_e_propiocepcion.mp4",
        "text": "Para realizar el ejercicio de propiocepción a una pierna, colócate de pie en una superficie estable. Levanta lentamente una pierna flexionando la rodilla y mantén el equilibrio sobre la pierna de apoyo. Activa los músculos del tobillo, la rodilla y el abdomen para estabilizar tu postura. Fija tu mirada en un punto fijo al frente para ayudarte. Si pierdes el equilibrio, apoya el pie suavemente y vuelve a intentarlo. Respira con calma y mantén la espalda totalmente erguida."
    },
    {
        "file": "ve_sentadilla.MOV",
        "out": "v_e_sentadilla.mp4",
        "text": "Para hacer la sentadilla correctamente, coloca los pies a la anchura de los hombros con las puntas ligeramente hacia afuera. Inicia el movimiento llevando la cadera hacia atrás y hacia abajo, como si fueras a sentarte en una silla. Inhala mientras desciendes, manteniendo el pecho erguido y la espalda recta. Asegúrate de que tus rodillas sigan la línea de tus pies sin hundirse hacia adentro. Baja hasta romper el paralelo, exhala y empuja con los talones para volver a subir."
    }
]

def generate_audio(text, output_path):
    subprocess.run(["say", "-v", "Mónica", "-r", "120", "-o", output_path, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", output_path, "temp.mp3"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(output_path)
    return "temp.mp3"

def process_video(input_vid, text, output_vid):
    print(f"Procesando {input_vid}...")
    
    audio_file = generate_audio(text, "temp.aiff")
    
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", input_vid,
        "-i", audio_file,
        "-filter_complex", "[1:a]apad[A]",
        "-map", "0:v", "-map", "[A]",
        "-c:v", "libx264", "-c:a", "aac",
        "-t", "30",
        "-pix_fmt", "yuv420p",
        "videos_explicativos/" + output_vid
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(audio_file)
    print(f"-> Guardado {output_vid}")

for v in videos_info:
    process_video(v["file"], v["text"], v["out"])

print("Todos los vídeos procesados correctamente.")
