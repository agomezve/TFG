/* Modo demostración sin servidor (GitHub Pages).
 *
 * Se carga antes que app.js y hace de servidor dentro del navegador:
 *  - fetch("/api/...") responde con los datos capturados del servidor real (demo/datos.json),
 *    con pacientes FICTICIOS. Lo que se cambia (plan, consentimiento, series nuevas…) se guarda
 *    solo en este navegador.
 *  - WebSocket("/ws/serie") reproduce una serie ya analizada por el motor real (MediaPipe) con el
 *    vídeo de ejemplo: GitHub Pages no puede ejecutar el análisis.
 * Las fechas se desplazan para que la demo parezca siempre «de hoy».
 */
(() => {
  "use strict";
  window.DEMO = true;
  const fetchReal = window.fetch.bind(window);
  const CLAVE = "demo-estado-v1";
  const CLINICA = "Clínica demo TeleRehab";

  // ─── Fechas ──────────────────────────────────────────────────────────────────
  const dos = (n) => String(n).padStart(2, "0");
  const fechaLocal = (d) => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
  const ahoraTexto = () => { const d = new Date(); return `${fechaLocal(d)} ${dos(d.getHours())}:${dos(d.getMinutes())}:${dos(d.getSeconds())}`; };
  const diaDe = (t) => { const [a, m, d] = t.slice(0, 10).split("-").map(Number); return new Date(a, m - 1, d); };
  const RE_FECHA = /^\d{4}-\d{2}-\d{2}/;
  function desplazar(obj, dias) {
    const mover = (t) => { const d = diaDe(t); d.setDate(d.getDate() + dias); return fechaLocal(d) + t.slice(10); };
    const andar = (v) => {
      if (typeof v === "string") return RE_FECHA.test(v) ? mover(v) : v;
      if (Array.isArray(v)) return v.map(andar);
      if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [RE_FECHA.test(k) || k.includes("|") ? k.replace(/\d{4}-\d{2}-\d{2}/, (f) => mover(f)) : k, andar(x)]));
      return v;
    };
    return andar(obj);
  }

  // ─── Estado de la demo ───────────────────────────────────────────────────────
  let D = null, E = null;  // datos capturados (fijos) y estado modificable
  const listo = fetchReal("/demo/datos.json").then((r) => r.json()).then((crudo) => {
    const dias = Math.round((diaDe(fechaLocal(new Date())) - diaDe(crudo.generado)) / 864e5);
    D = desplazar(crudo, dias);
    try { E = JSON.parse(localStorage.getItem(CLAVE)); } catch (_) { E = null; }
    if (!E || E.generado !== D.generado) E = estadoInicial();
  });
  function estadoInicial() {
    const pac = {};
    for (const p of D.fisio.pacientes) {
      const h = D.fisio.historiales[p.id];
      pac[p.id] = {
        id: p.id, nombre: p.nombre, edad: p.edad, sesiones: h.sesiones,
        plan: h.plan.map(({ ejercicio, nivel, series, dias_semana }) => ({ ejercicio, nivel, series, dias_semana })),
        consentimiento: null, alertas: h.alertas,
      };
    }
    return { generado: D.generado, pac, series: {}, siguienteId: Math.max(...Object.keys(pac).map(Number)) + 1, invitado: null };
  }
  const persistir = () => { try { localStorage.setItem(CLAVE, JSON.stringify(E)); } catch (_) { } };

  // Mismo cálculo que adherencia.py (plan_de_hoy y % de adherencia de los últimos 7 días)
  function planDeHoy(p) {
    const hoy = diaDe(fechaLocal(new Date())), hace7 = new Date(hoy); hace7.setDate(hoy.getDate() - 6);
    return p.plan.map((item) => {
      const delEj = p.sesiones.filter((s) => s.ejercicio === item.ejercicio);
      const hoyN = delEj.filter((s) => +diaDe(s.fecha) === +hoy).length;
      const semana = delEj.filter((s) => diaDe(s.fecha) >= hace7 && diaDe(s.fecha) <= hoy).length;
      return { ...item, hechas_hoy: hoyN, hechas_semana: semana, objetivo_semana: item.series * item.dias_semana, completado_hoy: hoyN >= item.series };
    });
  }
  function resumen(p) {
    const detalle = planDeHoy(p);
    const objetivo = detalle.reduce((a, d) => a + d.objetivo_semana, 0);
    const hechas = detalle.reduce((a, d) => a + Math.min(d.hechas_semana, d.objetivo_semana), 0);
    const ultima = p.sesiones.length ? p.sesiones.map((s) => s.fecha.slice(0, 10)).sort().pop() : null;
    const diasSin = ultima ? Math.round((diaDe(fechaLocal(new Date())) - diaDe(ultima)) / 864e5) : null;
    let alertas = (p.alertas || []).filter((a) => !["sin_plan", "sin_sesiones", "inactivo"].includes(a.tipo));
    if (!p.plan.length) alertas = [{ tipo: "sin_plan", gravedad: "info", texto: "Sin plan de ejercicios asignado" }, ...alertas];
    if (!ultima) alertas.push({ tipo: "sin_sesiones", gravedad: "media", texto: "Todavía no ha hecho ninguna serie" });
    return { adherencia: p.plan.length && objetivo ? Math.round(100 * hechas / objetivo) : null, dias_sin_entrenar: diasSin, ultima, alertas };
  }
  const versionConsentimiento = () => Object.values(D.pacientes)[0].consentimiento.version_actual;
  const vigente = (p) => !!(p.consentimiento && p.consentimiento.version === versionConsentimiento());
  const loginPaciente = (p) => ({ token: "demo-" + p.id, rol: "paciente", id: p.id, nombre: p.nombre, consentimiento: vigente(p) });
  const buscarPaciente = (nombre) => Object.values(E.pac).find((p) => p.nombre.toLowerCase() === String(nombre || "").trim().toLowerCase());

  // ─── fetch("/api/...") ───────────────────────────────────────────────────────
  const responder = (datos, estado = 200) => new Response(JSON.stringify(datos), { status: estado, headers: { "Content-Type": "application/json" } });
  const fallo = (estado, detalle) => responder({ detalle }, estado);
  const espera = () => new Promise((r) => setTimeout(r, 120 + Math.random() * 160));  // que parezca red

  window.fetch = async (entrada, opciones = {}) => {
    const url = new URL(typeof entrada === "string" ? entrada : entrada.url, location.href);
    // PDF, CSV y QR son ficheros estáticos ya generados
    if (url.origin !== location.origin || !url.pathname.startsWith("/api/") || /\.(pdf|csv|svg)$/.test(url.pathname)) return fetchReal(entrada, opciones);
    await listo; await espera();
    const metodo = (opciones.method || "GET").toUpperCase();
    const cab = opciones.headers || {};
    const token = ((cab.Authorization || cab.authorization || "").slice(7)) || url.searchParams.get("token") || "";
    const cuerpo = (() => { try { return JSON.parse(opciones.body || "{}"); } catch (_) { return {}; } })();
    const ruta = url.pathname;
    const usuario = token === "demo-fisio" ? { rol: "fisio" } : token.startsWith("demo-") && E.pac[token.slice(5)] ? { rol: "paciente", p: E.pac[token.slice(5)] } : null;
    let m;

    if (ruta === "/api/login" && metodo === "POST") {
      const u = String(cuerpo.usuario || "").trim().toLowerCase();
      if (u === "fisio") return responder({ token: "demo-fisio", ...D.fisio.login });
      const p = buscarPaciente(u);
      return p ? responder(loginPaciente(p)) : fallo(401, "En la demo entra como fisio, Carmen, Julian o Lucia");
    }
    if (ruta === "/api/logout") return responder({ ok: true });
    if ((m = ruta.match(/^\/api\/invitacion\/([\w-]+)$/))) {
      const p = E.invitado && E.pac[E.invitado];
      if (!p) return fallo(404, "La invitación no es válida o ha caducado. Pide a tu fisioterapeuta una nueva.");
      if (metodo === "GET") return responder({ nombre: p.nombre, clinica: CLINICA });
      if ((cuerpo.password || "").length < 6) return fallo(400, "La contraseña debe tener al menos 6 caracteres");
      if (cuerpo.password !== cuerpo.password2) return fallo(400, "Las contraseñas no coinciden");
      E.invitado = null; persistir();
      return responder(loginPaciente(p));
    }
    if (!usuario) return fallo(401, "Sesión caducada");
    if (ruta === "/api/ejercicios") return responder(D.ejercicios);

    // Paciente
    if (usuario.rol === "paciente") {
      const p = usuario.p;
      if (ruta === "/api/mi-historial") return responder(p.sesiones);
      if (ruta === "/api/mi-plan") { const r = resumen(p); return responder({ plan: planDeHoy(p), adherencia: r.adherencia, dias_sin_entrenar: r.dias_sin_entrenar, ultima: r.ultima, alertas: r.alertas }); }
      if (ruta === "/api/mi-password") return responder({ ok: true });
      if (ruta === "/api/consentimiento") {
        if (metodo === "GET") return responder({ version_actual: versionConsentimiento(), aceptado: vigente(p), fecha: p.consentimiento ? p.consentimiento.fecha : null });
        if (metodo === "POST") {
          if (cuerpo.version !== versionConsentimiento() || cuerpo.acepto !== true) return fallo(400, "Debes aceptar la versión vigente del consentimiento");
          p.consentimiento = { version: cuerpo.version, fecha: ahoraTexto() }; persistir(); return responder({ ok: true });
        }
        if (metodo === "DELETE") { p.consentimiento = null; persistir(); return responder({ ok: true }); }
      }
      if (ruta === "/api/mis-datos") return new Response(JSON.stringify({ paciente: p.nombre, exportado: ahoraTexto(), demo: true, consentimiento: p.consentimiento, plan: p.plan, sesiones: p.sesiones }, null, 2), { headers: { "Content-Type": "application/json" } });
      return fallo(403, "No permitido");
    }

    // Fisioterapeuta
    if (ruta === "/api/fisio/pacientes" && metodo === "GET") {
      return responder(Object.values(E.pac).map((p) => {
        const r = resumen(p);
        return { id: p.id, nombre: p.nombre, edad: p.edad, series: p.sesiones.length, ultima: p.sesiones[0] ? p.sesiones[0].fecha : null, en_plan: p.plan.length, ...r };
      }));
    }
    if (ruta === "/api/fisio/pacientes" && metodo === "POST") {
      const nombre = String(cuerpo.nombre || "").trim();
      if (!nombre) return fallo(400, "El nombre es obligatorio");
      if (nombre.toLowerCase() === "fisio" || buscarPaciente(nombre)) return fallo(400, "Ya existe un paciente con ese nombre");
      if (cuerpo.password && cuerpo.password.length < 6) return fallo(400, "La contraseña debe tener al menos 6 caracteres");
      if (cuerpo.password && cuerpo.password !== cuerpo.password2) return fallo(400, "Las contraseñas no coinciden");
      const edad = String(cuerpo.edad || "").trim();
      if (edad && !/^\d+$/.test(edad)) return fallo(400, "La edad debe ser un número");
      const id = E.siguienteId++;
      E.pac[id] = { id, nombre, edad: edad ? +edad : null, sesiones: [], plan: [], consentimiento: null, alertas: [] };
      if (!cuerpo.password) E.invitado = id;
      persistir();
      return responder({ id, nombre, invitacion: cuerpo.password ? null : invitacion() });
    }
    if ((m = ruta.match(/^\/api\/fisio\/pacientes\/(\d+)(\/\w+)?$/))) {
      const p = E.pac[m[1]];
      if (!p) return fallo(404, "Paciente no encontrado");
      if (m[2] === "/historial") {
        const r = resumen(p);
        return responder({ nombre: p.nombre, sesiones: p.sesiones, plan: planDeHoy(p), ...r,
          consentimiento: p.consentimiento ? { version: p.consentimiento.version, fecha: p.consentimiento.fecha, vigente: vigente(p) } : null });
      }
      if (m[2] === "/plan" && metodo === "PUT") {
        const items = (cuerpo.plan || []).map((i) => ({ ejercicio: i.ejercicio, nivel: i.nivel, series: +i.series, dias_semana: +i.dias_semana }));
        if (items.some((i) => !(i.series >= 1 && i.series <= 10 && i.dias_semana >= 1 && i.dias_semana <= 7))) return fallo(400, "Series entre 1 y 10, días por semana entre 1 y 7");
        p.plan = items; persistir(); return responder({ ok: true, plan: items });
      }
      if (m[2] === "/invitacion") { E.invitado = p.id; persistir(); return responder(invitacion()); }
      if (!m[2] && metodo === "DELETE") {
        if (String(cuerpo.confirmacion || "").trim().toLowerCase() !== p.nombre.toLowerCase()) return fallo(400, "Escribe el nombre del paciente para confirmar");
        delete E.pac[p.id]; persistir(); return responder({ ok: true });
      }
    }
    if (ruta === "/api/fisio/serie") {
      const clave = `${url.searchParams.get("paciente_id")}|${url.searchParams.get("ts")}`;
      return responder(E.series[clave] || D.series[clave] || { informe: null, video: null });
    }
    if (ruta === "/api/fisio/metricas") return responder(D.fisio.metricas);
    if (ruta === "/api/fisio/password") return responder({ ok: true });
    return fallo(404, "No disponible en la demo");
  };
  function invitacion() {
    const d = new Date(); d.setDate(d.getDate() + 7);
    return { codigo: "demo", caduca: `${fechaLocal(d)} ${dos(d.getHours())}:${dos(d.getMinutes())}:00` };
  }

  // ─── WebSocket("/ws/serie"): reproduce una serie ya analizada ─────────────────
  const WSReal = window.WebSocket;
  class SerieGrabada {
    constructor(direccion) {
      const url = new URL(direccion, location.href);
      if (!url.pathname.startsWith("/ws/serie")) return new WSReal(direccion);
      this.readyState = 0; this.binaryType = "blob";
      this.ejercicio = url.searchParams.get("ejercicio"); this.nivel = url.searchParams.get("nivel");
      this.token = url.searchParams.get("token") || "";
      this.pendientes = 0; this.fin = false;
      listo.then(() => this._abrir());
    }
    _emitir(data) { this.onmessage && this.onmessage({ data }); }
    _abrir() {
      const p = E.pac[this.token.slice(5)];
      if (!p) { this.readyState = 1; this.onopen && this.onopen(); return this._emitir(JSON.stringify({ estado: "error", mensaje: "Sesión no válida" })); }
      if (!vigente(p)) {
        this.readyState = 1; this.onopen && this.onopen();
        return this._emitir(JSON.stringify({ estado: "error", mensaje: "Antes de grabar tienes que aceptar el consentimiento" }));
      }
      this.p = p; this.serie = D.directo[this.ejercicio];
      const v = this.video = document.createElement("video");
      Object.assign(v, { muted: true, playsInline: true, preload: "auto", src: this.serie.video });
      v.setAttribute("playsinline", ""); v.setAttribute("aria-hidden", "true");
      v.style.cssText = "position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none";
      document.body.appendChild(v);
      this.lienzo = document.createElement("canvas");
      v.onended = () => this._terminar(this.serie.resultado === "en_curso" ? "detenido" : this.serie.resultado);
      v.play().catch(() => { });
      this.readyState = 1; this.onopen && this.onopen();
      this.reloj = setInterval(() => this._tic(), 55);
    }
    _marcador() {
      const t = this.video.currentTime;
      let fila = this.serie.linea[0];
      for (const f of this.serie.linea) { if (f[0] <= t) fila = f; else break; }
      return { errores: fila[1], persona_detectada: !!fila[2], estado: fila[3], estado_esqueleto: "neutro", preparacion: 0 };
    }
    _tic() {
      if (this.fin || !this.pendientes || this.video.readyState < 2 || !this.video.videoWidth) return;
      this.pendientes--;
      const v = this.video, c = this.lienzo;
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d").drawImage(v, 0, 0);
      const m = this._marcador();
      c.toBlob((b) => {
        if (this.fin) return;
        b && this._emitir(b);
        if (m.estado === "completado" || m.estado === "cortafuegos") {
          this._emitir(JSON.stringify(m));
          return this._terminar(m.estado);
        }
        this._emitir(JSON.stringify({ ...m, estado: "en_curso" }));
      }, "image/jpeg", 0.8);
    }
    _terminar(resultado) {
      if (this.fin) return;
      this.fin = true; clearInterval(this.reloj);
      // Igual que el servidor: guarda la serie (con el informe real del motor) y avisa
      const fecha = ahoraTexto(), d = this.serie, p = this.p;
      p.sesiones.unshift({ fecha, ejercicio: this.ejercicio, nivel: this.nivel, repeticiones: d.repeticiones || 0,
        errores: this._marcador().errores, profundidad_media: null, observaciones: "" });
      E.series[`${p.id}|${fecha}`] = { informe: d.informe || null, video: d.video };
      persistir();
      setTimeout(() => {
        this.video.pause(); this.video.remove();
        this._emitir(JSON.stringify({ estado: "guardado", resultado }));
        this.readyState = 3;
      }, 700);
    }
    send(datos) {
      if (this.fin || !this.video) return;
      if (datos === "stop") return this._terminar("detenido");
      this.pendientes = Math.min(2, this.pendientes + 1);
    }
    close() { this.fin = true; clearInterval(this.reloj); this.video && (this.video.pause(), this.video.remove()); this.readyState = 3; }
  }
  window.WebSocket = SerieGrabada;

  // ─── Ajustes de interfaz para la demo ───────────────────────────────────────
  const estilo = document.createElement("style");
  estilo.textContent = `
    body.demo [data-fuente="user"], body.demo [data-fuente="environment"], body.demo [data-fuente="archivo"],
    body.demo .hoja .lista > .alerta { display: none !important; }
    .demo-nota { display: flex; gap: 10px; align-items: flex-start; margin: 0 0 12px; padding: 12px 14px; border-radius: 14px;
      background: var(--azul-suave); color: var(--texto); font-size: 14px; line-height: 1.45; }
    .demo-nota svg { flex: none; width: 18px; height: 18px; margin-top: 1px; color: var(--azul); }
    .demo-accesos { margin-top: 16px; background: var(--superficie); border: 1px solid var(--borde); border-radius: 20px;
      padding: 16px 16px 14px; box-shadow: var(--sombra-1); }
    .demo-accesos h2 { margin: 0 0 4px; font-size: 15px; }
    .demo-accesos p { margin: 0 0 12px; color: var(--texto-2); font-size: 13.5px; line-height: 1.45; }
    .demo-accesos .rejilla { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .demo-accesos button { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 12px; border-radius: 12px;
      border: 1px solid var(--borde); background: var(--superficie-2); color: var(--texto); font: inherit; text-align: left; cursor: pointer; }
    .demo-accesos button b { font-size: 14.5px; }
    .demo-accesos button small { color: var(--texto-2); font-size: 12px; }
    .demo-accesos button:hover, .demo-accesos button:focus-visible { border-color: var(--acento); }`;
  document.head.appendChild(estilo);

  const ACCESOS = [
    ["fisio", "Fisioterapeuta", "Panel de la clínica"],
    ["Carmen", "Carmen, 71", "Prótesis de rodilla"],
    ["Julian", "Julian, 45", "Manguito rotador"],
    ["Lucia", "Lucia, 28", "Readaptación LCA"],
  ];
  const icono = (n) => `<svg class="ic" aria-hidden="true"><use href="#i-${n}"/></svg>`;
  function retocar() {
    document.body.classList.add("demo");
    const form = document.getElementById("f-login");
    if (form && !document.querySelector(".demo-accesos")) {
      const caja = document.createElement("section");
      caja.className = "demo-accesos";
      caja.innerHTML = `<h2>Demo con pacientes ficticios</h2>
        <p>Entra con un toque. Los cambios que hagas solo se guardan en este navegador.</p>
        <div class="rejilla">${ACCESOS.map(([u, t, s]) => `<button type="button" data-u="${u}"><b>${t}</b><small>${s}</small></button>`).join("")}</div>`;
      form.after(caja);
      caja.querySelectorAll("[data-u]").forEach((b) => (b.onclick = () => {
        document.getElementById("u").value = b.dataset.u;
        document.getElementById("p").value = "demo";
        form.requestSubmit ? form.requestSubmit() : form.querySelector("button[type=submit]").click();
      }));
    }
    const lista = document.querySelector(".hoja [data-fuente='ejemplo']")?.parentElement;
    if (lista && !lista.querySelector(".demo-nota")) {
      lista.insertAdjacentHTML("afterbegin", `<div class="demo-nota">${icono("info")}<span>En esta demo web se reproduce una serie ya analizada por el motor de visión artificial. La corrección con la cámara en directo funciona en la app conectada al servidor de la clínica.</span></div>`);
    }
    // El vídeo de cada serie (fisio) es un fichero estático, no pasa por /api/fisio/video
    document.querySelectorAll("video[src^='/api/fisio/video']").forEach((v) => {
      const ruta = new URL(v.src, location.href).searchParams.get("ruta");
      if (ruta) v.src = ruta;
    });
  }
  new MutationObserver(retocar).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener("DOMContentLoaded", retocar);
})();
