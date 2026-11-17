# Poner la app en internet con una dirección fija

Hay dos caminos. Los dos dan HTTPS de verdad (sin avisos de certificado), que es lo que necesita el móvil para usar la cámara.

## Opción A: servidor en la nube (recomendada para el piloto y para Wolaria)

La app funciona 24 horas sin depender de tu Mac.

**Qué necesitas**
- Un VPS en la Unión Europea con 2 vCPU y 4 GB de RAM: Hetzner CX22, OVH o similar. Cuesta unos 5–8 € al mes. Que esté en la UE importa por la protección de datos (RGPD).
- Un dominio, por ejemplo `telerehab.es`, por unos 10 € al año.

**Pasos**
1. Crea el VPS con Ubuntu e instala Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
2. En el panel de tu dominio, crea un registro **A**, por ejemplo `app`, que apunte a la IP del VPS.
3. Copia el proyecto al servidor:
   ```bash
   git clone https://github.com/agomezve/TFG.git
   ```
4. En `despliegue/Caddyfile`, cambia `app.tudominio.es` por tu dominio.
5. Arráncalo:
   ```bash
   cd TFG/TFG_AGV/despliegue && docker compose up -d --build
   ```
6. Abre `https://app.tudominio.es`. Caddy consigue el certificado HTTPS él solo.

Al arrancar por primera vez, la contraseña del fisio es `12345`. **Cámbiala nada más entrar**, desde Ajustes.

Los datos se guardan en el volumen `datos` de Docker. Para hacer una copia de seguridad:

```bash
docker run --rm -v despliegue_datos:/d -v $PWD:/b alpine tar czf /b/copia_datos.tgz -C /d .
```

## Opción B: túnel de Cloudflare con tu dominio (gratis, pero depende del Mac)

Sirve para demos. La dirección es fija, pero el Mac tiene que estar encendido.

1. Crea una cuenta gratuita en Cloudflare y pasa tu dominio a Cloudflare: cambiar los DNS se hace en el panel donde compraste el dominio.
2. Inicia sesión desde el Mac:
   ```bash
   ~/.local/bin/cloudflared tunnel login
   ```
3. Crea el túnel:
   ```bash
   ~/.local/bin/cloudflared tunnel create telerehab
   ```
4. Enlaza el túnel con tu dominio:
   ```bash
   ~/.local/bin/cloudflared tunnel route dns telerehab app.tudominio.es
   ```
5. Lanza el túnel:
   ```bash
   ~/.local/bin/cloudflared tunnel run --url http://localhost:8000 telerehab
   ```

## Antes de usarla con pacientes reales

- Rellena los datos del responsable en `web/privacidad.html`: el centro, su CIF y su contacto.
- Firma un contrato de encargado del tratamiento con cada clínica (artículo 28 del RGPD).
- Haz copias de seguridad periódicas del volumen de datos.
