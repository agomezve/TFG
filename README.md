# TeleRehab IA: telerehabilitación con visión artificial

Plataforma de telerehabilitación que, usando **solo una cámara**, analiza en tiempo real los ejercicios del paciente (sentadilla, plancha, hip thrust, etc.). Cuenta repeticiones, detecta errores de ejecución y genera informes clínicos que revisa el fisioterapeuta.

> Trabajo Fin de Grado de Aarón Gómez Vera. El código de la aplicación está en [`TFG_AGV/`](TFG_AGV).

## Funcionalidades

**Paciente**
- 10 ejercicios guiados, cada uno en 3 niveles (principiante, intermedio y avanzado):
  - Sentadilla
  - Peso muerto
  - Press militar
  - Press banca
  - Plancha
  - Propiocepción
  - Elevaciones laterales
  - Hip thrust
  - Zancadas
  - Búlgaras
- Corrección en tiempo real por voz y en pantalla, basada en ángulos articulares 3D (MediaPipe Pose).
- Vídeo explicativo y consejos de cada ejercicio.
- Estadísticas personales.

**Fisioterapeuta**
- Alta de pacientes con contraseña propia.
- Calendario de sesiones por paciente.
- Detalle de cada serie, con informe clínico y grabación.
- Gráfica de evolución diaria: repeticiones correctas o con error y % de ejecución correcta.
- Cambio de contraseña del fisioterapeuta.

## Instalación

Requiere Python 3.11 y ffmpeg, que se usa para convertir las grabaciones a MP4.

```bash
cd TFG_AGV
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python pantalla_principal.py
```

Para enseñarla sin datos reales hay una demo con pacientes ficticios y 6 semanas de sesiones:

```bash
python scripts/crear_datos_demo.py
TELEREHAB_DATA_DIR=datos_demo python pantalla_principal.py
```

Credenciales de la demo:
- Fisioterapeuta: `fisio` / `12345`
- Pacientes: `Carmen`, `Julian` o `Lucia`, con la contraseña `demo1234`

La variable `TELEREHAB_DATA_DIR` indica dónde se guardan los datos: base de datos, informes y grabaciones. Si no se define, se usan los de la carpeta del código.

## Tests

```bash
python -m unittest discover -s tests -v
```

- **Regresión (golden master):** reproduce 11 vídeos reales en los 3 niveles y comprueba que repeticiones, errores, informes y registros en la base de datos son idénticos a la referencia. Así cualquier mejora puede hacerse sin romper la lógica clínica.
- **Básicos:** cubren cálculo de ángulos, hash de contraseñas, base de datos (incluida la migración de BBDD antiguas) y coherencia del catálogo de ejercicios.
- **Interfaz:** recorre las pantallas del paciente y del fisio con una base de datos temporal.

## Arquitectura

| Archivo | Responsabilidad |
|---|---|
| `pantalla_principal.py` | Interfaz (CustomTkinter): login, paciente y fisioterapeuta |
| `modulos/` | Un módulo de análisis biomecánico por ejercicio (hereda de `modulo_base.py`) |
| `ejercicios.py` | Catálogo único de ejercicios: módulo, carpeta de informes y vídeo |
| `database.py` | SQLite: pacientes, sesiones, autenticación y migraciones |
| `seguridad.py` | Hash de contraseñas (PBKDF2-SHA256 con sal) |
| `graficas.py` | Gráfica de progreso del paciente |
| `config.py` | Rutas de datos y utilidades multiplataforma |

## Privacidad

Los datos de pacientes (`pacientes.db`, `usuarios/`, grabaciones) **no se suben al repositorio** (ver `.gitignore`). Las contraseñas se guardan con hash, nunca en texto plano. El análisis de vídeo se hace en local: las imágenes no salen del equipo.
