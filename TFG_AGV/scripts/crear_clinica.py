"""Da de alta una clínica nueva con su fisioterapeuta, o añade un fisio a una clínica existente.

Cada clínica solo ve a sus pacientes. La clínica 1 es la de siempre (usuario "fisio").

Uso (desde TFG_AGV/):
    python scripts/crear_clinica.py --listar
    python scripts/crear_clinica.py "Fisio Salamanca" --usuario laura
    python scripts/crear_clinica.py --clinica 2 --usuario pedro          # otro fisio en la clínica 2
    python scripts/crear_clinica.py --renombrar 1 "Clínica Aarón"

La contraseña se pide por teclado; si no se escribe ninguna, se genera una aleatoria y se muestra una vez.
Con TELEREHAB_DATA_DIR se elige la carpeta de datos (p. ej. datos_prueba).
"""
import argparse
import getpass
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("nombre", nargs="?", help="nombre de la clínica nueva")
    p.add_argument("--usuario", help="usuario del fisioterapeuta")
    p.add_argument("--nombre-fisio", help="nombre que se muestra del fisio (por defecto, el usuario)")
    p.add_argument("--clinica", type=int, help="añadir el fisio a esta clínica en vez de crear una")
    p.add_argument("--listar", action="store_true", help="lista las clínicas")
    p.add_argument("--renombrar", type=int, metavar="ID", help="cambia el nombre de la clínica ID por NOMBRE")
    a = p.parse_args()
    database.init_db()

    if a.listar:
        for cid, nombre, n_fisios, n_pacientes in database.obtener_clinicas():
            print(f"{cid:>3}  {nombre:<30} {n_fisios} fisio(s)  {n_pacientes} paciente(s)")
        return
    if a.renombrar:
        if not a.nombre:
            p.error("indica el nuevo nombre")
        database.renombrar_clinica(a.renombrar, a.nombre)
        print(f"Clínica {a.renombrar} renombrada a «{a.nombre}»")
        return
    if not a.usuario or not (a.nombre or a.clinica):
        p.error("indica el nombre de la clínica (o --clinica ID) y --usuario")
    if database.existe_usuario_fisio(a.usuario) or database.existe_paciente(a.usuario):
        sys.exit(f"El usuario «{a.usuario}» ya está en uso")

    password = getpass.getpass("Contraseña del fisio (Intro para generar una): ") if sys.stdin.isatty() else ""
    generada = not password
    if generada:
        password = secrets.token_urlsafe(9)
    elif len(password) < 6:
        sys.exit("La contraseña debe tener al menos 6 caracteres")

    clinica_id = a.clinica or database.crear_clinica(a.nombre)
    database.crear_fisio(a.usuario, password, clinica_id, a.nombre_fisio)
    print(f"Clínica {clinica_id} «{database.nombre_clinica(clinica_id)}»: fisio «{a.usuario}» creado.")
    if generada:
        print(f"Contraseña: {password}   (apúntala: no se vuelve a mostrar)")


if __name__ == "__main__":
    main()
