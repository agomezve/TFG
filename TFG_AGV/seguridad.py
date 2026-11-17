"""Utilidades de seguridad: hash de contraseñas con PBKDF2-SHA256 (librería estándar).

Las contraseñas nunca se guardan en claro; se guarda "pbkdf2_sha256$iteraciones$sal$hash".
"""
import hashlib
import hmac
import secrets

_ALGORITMO = "pbkdf2_sha256"
_ITERACIONES = 240_000


def generar_hash(password: str) -> str:
    sal = secrets.token_hex(16)
    derivada = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sal), _ITERACIONES)
    return f"{_ALGORITMO}${_ITERACIONES}${sal}${derivada.hex()}"


def verificar_hash(password: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = almacenado.split("$")
        if algoritmo != _ALGORITMO:
            return False
        derivada = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
        return hmac.compare_digest(derivada.hex(), esperado)
    except (ValueError, AttributeError):
        return False
