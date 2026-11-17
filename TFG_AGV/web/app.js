"use strict";
/* App móvil de TeleRehab IA (PWA). Sin dependencias: HTML + CSS + JS.
   La cámara se usa en el móvil y el análisis lo hace el servidor Python con los mismos
   módulos de ejercicio que la app de escritorio. */

// ─── Estado y utilidades ──────────────────────────────────────────────────────
const S = { token: null, usuario: null, ejercicios: null };
const app = document.getElementById("app");

const NOMBRES = { Propiocepcion: "Propiocepción", Bulgaras: "Búlgaras" };
const EMOJIS = {
  "Sentadilla": "🦵", "Peso Muerto": "🏋️", "Press Militar": "🙌", "Press Banca": "💪",
  "Plancha": "⏱️", "Propiocepcion": "🦩", "Hombros Laterales": "🤸", "Hip Thrust": "🌉",
  "Zancadas": "🚶", "Bulgaras": "🪑",
};
const NIVELES = [["principiante", "Principiante"], ["intermedio", "Intermedio"], ["avanzado", "Avanzado"]];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

const nombreVisible = (n) => NOMBRES[n] || n;
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fechaCorta = (iso) => { const [a, m, d] = iso.slice(0, 10).split("-"); return `${+d} ${MESES[+m - 1]} ${a}`; };
const esPorTiempo = (ej) => ej === "Plancha" || ej === "Propiocepcion";

function guardar(clave, valor) { try { valor == null ? localStorage.removeItem(clave) : localStorage.setItem(clave, JSON.stringify(valor)); } catch (_) { } }
function leer(clave) { try { return JSON.parse(localStorage.getItem(clave)); } catch (_) { return null; } }

async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, {
    ...opciones,
    headers: { "Content-Type": "application/json", ...(S.token ? { Authorization: "Bearer " + S.token } : {}) },
  });
  const datos = await r.json().catch(() => ({}));
  if (r.status === 401 && S.token) { cerrarSesion(); throw new Error(datos.detalle || "Sesión caducada"); }
  if (!r.ok) throw new Error(datos.detalle || "Error de conexión");
  return datos;
}

function aviso(texto) {
  const el = document.getElementById("aviso");
  el.textContent = texto; el.hidden = false;
  clearTimeout(aviso.t); aviso.t = setTimeout(() => (el.hidden = true), 2600);
}

function hablar(texto) {
  try {
    const u = new SpeechSynthesisUtterance(texto); u.lang = "es-ES";
    speechSynthesis.cancel(); speechSynthesis.speak(u);
  } catch (_) { }
}

// ─── Navegación (con soporte del botón "atrás" del móvil) ─────────────────────
const pila = [];
function ir(vista, { reemplazar = false } = {}) {
  if (reemplazar) pila.pop(); else history.pushState({ n: pila.length + 1 }, "");
  pila.push(vista);
  cerrarHoja(); window.scrollTo(0, 0);
  vista();
}
function volver() { history.back(); }
window.addEventListener("popstate", () => {
  if (limpiezaDirecto) { limpiezaDirecto(); }
  if (!document.getElementById("hoja").hidden) { cerrarHoja(); history.pushState({}, ""); return; }
  if (pila.length > 1) { pila.pop(); window.scrollTo(0, 0); pila[pila.length - 1](); }
  else history.pushState({}, "");
});
function inicio(vista) { pila.length = 0; pila.push(vista); history.replaceState({ n: 1 }, ""); vista(); }

function cabecera(titulo, { atras = true, derecha = "" } = {}) {
  return `<header class="cabecera">
    ${atras ? `<button class="btn-icono" data-atras aria-label="Volver">←</button>` : ""}
    <h1>${esc(titulo)}</h1>${derecha}</header>`;
}
function pintar(html, alPintar) {
  app.innerHTML = html;
  app.querySelectorAll("[data-atras]").forEach((b) => (b.onclick = volver));
  alPintar && alPintar();
}

// ─── Hoja inferior ────────────────────────────────────────────────────────────
function abrirHoja(html, alPintar) {
  const hoja = document.getElementById("hoja");
  document.getElementById("hoja-contenido").innerHTML = html;
  hoja.hidden = false;
  hoja.querySelectorAll("[data-cerrar]").forEach((b) => (b.onclick = cerrarHoja));
  alPintar && alPintar(hoja);
}
function cerrarHoja() {
  const hoja = document.getElementById("hoja");
  hoja.querySelectorAll("video").forEach((v) => v.pause());
  hoja.hidden = true;
  document.getElementById("hoja-contenido").innerHTML = "";
}

// ─── Login ────────────────────────────────────────────────────────────────────
function pantallaLogin() {
  pintar(`<main class="pantalla login">
    <div class="marca">
      <img src="/static/icono-192.png" alt="">
      <h1>TeleRehab IA</h1>
      <p>Tu rehabilitación en casa, corregida en tiempo real por visión artificial.</p>
    </div>
    <form id="f-login" autocomplete="on" novalidate>
      <div class="campo"><label for="u">Usuario</label>
        <input id="u" name="username" autocomplete="username" autocapitalize="words" placeholder="Tu nombre" required></div>
      <div class="campo"><label for="p">Contraseña</label>
        <input id="p" name="password" type="password" autocomplete="current-password" placeholder="••••••" required></div>
      <p class="error" id="err"></p>
      <button class="btn" type="submit">Entrar</button>
    </form>
  </main>`, () => {
    document.getElementById("f-login").onsubmit = async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector("button"); btn.disabled = true;
      try {
        const r = await api("/api/login", { method: "POST", body: JSON.stringify({ usuario: document.getElementById("u").value, password: document.getElementById("p").value }) });
        S.token = r.token; S.usuario = r; guardar("sesion", r);
        if (r.rol === "paciente" && !r.consentimiento) inicio(pantallaConsentimiento);
        else entrar();
      } catch (err) { document.getElementById("err").textContent = err.message; btn.disabled = false; }
    };
  });
}

function cerrarSesion() {
  if (S.token) fetch("/api/logout", { method: "POST", headers: { Authorization: "Bearer " + S.token } }).catch(() => { });
  S.token = null; S.usuario = null; guardar("sesion", null);
  inicio(pantallaLogin);
}

function entrar() {
  if (S.usuario.rol === "fisio") inicio(() => fisioInicio());
  else inicio(() => pacienteInicio("hoy"));
}

// ─── Consentimiento (RGPD) ────────────────────────────────────────────────────
const TEXTO_PRIVACIDAD = `
  <p>Para corregir tus ejercicios, TeleRehab IA trata estos datos:</p>
  <ul>
    <li><b>Imagen de tu cámara</b> mientras haces una serie. Se analiza la postura y se guarda un vídeo de la serie.</li>
    <li><b>Resultados de cada serie</b>: repeticiones, errores, ángulos e informe.</li>
    <li><b>Tus datos de paciente</b>: nombre, edad y notas de tu fisioterapeuta.</li>
  </ul>
  <p><b>Para qué:</b> solo para tu rehabilitación y para que tu fisioterapeuta siga tu evolución. No se venden ni se usan para publicidad.</p>
  <p><b>Quién los ve:</b> tú y tu fisioterapeuta. Los vídeos solo los ve tu fisioterapeuta.</p>
  <p><b>Tus derechos:</b> desde <i>Mi cuenta</i> puedes descargar tus datos o retirar este consentimiento. Para borrarlos, pídeselo a tu fisioterapeuta.</p>
  <p><a class="enlace" href="/privacidad" target="_blank" rel="noopener">Leer la política de privacidad completa</a></p>`;

async function pantallaConsentimiento() {
  let version;
  try { version = (await api("/api/consentimiento")).version_actual; } catch (e) { return; }
  pintar(`<main class="pantalla">${cabecera("Tu privacidad", { atras: false })}
    <div class="contenido sin-tabs">
      <div class="saludo"><h2>Antes de empezar 🔒</h2><p>Tus datos de salud son tuyos. Así es como los cuidamos.</p></div>
      <div class="tarjeta privacidad-txt">${TEXTO_PRIVACIDAD}</div>
      <label class="check"><input type="checkbox" id="acepto">
        <span>He leído la información y doy mi consentimiento para que se traten mis datos de salud con esta finalidad.</span></label>
      <div class="fila-btns">
        <button class="btn" id="aceptar" disabled>Aceptar y continuar</button>
        <button class="btn fantasma" id="no">Ahora no (cerrar sesión)</button>
      </div>
    </div></main>`, () => {
    const check = document.getElementById("acepto"), boton = document.getElementById("aceptar");
    check.onchange = () => (boton.disabled = !check.checked);
    boton.onclick = async () => {
      boton.disabled = true;
      try { await api("/api/consentimiento", { method: "POST", body: JSON.stringify({ version, acepto: true }) }); entrar(); }
      catch (e) { aviso(e.message); boton.disabled = false; }
    };
    document.getElementById("no").onclick = cerrarSesion;
  });
}

function hojaCuentaPaciente() {
  abrirHoja(`<h2>Mi cuenta</h2>
    <div class="lista">
      <button class="item" id="c-pass"><span class="emoji">🔑</span><span class="txt"><b>Cambiar contraseña</b></span><span class="flecha">›</span></button>
      <button class="item" id="c-priv"><span class="emoji">🔒</span><span class="txt"><b>Privacidad y mis datos</b><small>Descargar, retirar consentimiento</small></span><span class="flecha">›</span></button>
    </div>
    <div class="fila-btns" style="margin-top:14px"><button class="btn secundario" id="c-salir">Cerrar sesión</button></div>`, (hoja) => {
    hoja.querySelector("#c-salir").onclick = () => { cerrarHoja(); cerrarSesion(); };
    hoja.querySelector("#c-pass").onclick = hojaPasswordPaciente;
    hoja.querySelector("#c-priv").onclick = hojaPrivacidadPaciente;
  });
}

function hojaPasswordPaciente() {
  abrirHoja(`<h2>Cambiar contraseña</h2>
    <form id="f-pass" novalidate>
      <div class="campo"><label for="a-act">Contraseña actual</label><input id="a-act" type="password" autocomplete="current-password"></div>
      <div class="dos-col">
        <div class="campo"><label for="a-n1">Nueva</label><input id="a-n1" type="password" autocomplete="new-password"></div>
        <div class="campo"><label for="a-n2">Repetir</label><input id="a-n2" type="password" autocomplete="new-password"></div>
      </div>
      <p class="error" id="a-err"></p>
      <div class="fila-btns"><button class="btn" type="submit">Guardar</button>
        <button class="btn fantasma" type="button" data-cerrar>Cancelar</button></div>
    </form>`, (hoja) => {
    hoja.querySelector("#f-pass").onsubmit = async (e) => {
      e.preventDefault();
      const v = (id) => hoja.querySelector(id).value;
      try {
        await api("/api/mi-password", { method: "POST", body: JSON.stringify({ actual: v("#a-act"), nueva: v("#a-n1"), nueva2: v("#a-n2") }) });
        cerrarHoja(); aviso("✅ Contraseña cambiada");
      } catch (err) { hoja.querySelector("#a-err").textContent = err.message; }
    };
  });
}

async function hojaPrivacidadPaciente() {
  let c = {};
  try { c = await api("/api/consentimiento"); } catch (_) { }
  abrirHoja(`<h2>Privacidad y mis datos</h2>
    <div class="privacidad-txt">${TEXTO_PRIVACIDAD}</div>
    <p class="receta">${c.fecha ? `Consentimiento aceptado el ${fechaCorta(c.fecha)}.` : ""}</p>
    <div class="fila-btns" style="margin-top:12px">
      <button class="btn secundario" id="p-descargar">⬇️ Descargar mis datos</button>
    </div>
    <div class="zona-peligro">
      <p>Si retiras el consentimiento no se grabarán más series hasta que lo vuelvas a aceptar. Para borrar todos tus datos, pídeselo a tu fisioterapeuta.</p>
      <button class="btn borde-rojo" id="p-retirar">Retirar consentimiento</button>
    </div>`, (hoja) => {
    hoja.querySelector("#p-descargar").onclick = async () => {
      try {
        const r = await fetch("/api/mis-datos", { headers: { Authorization: "Bearer " + S.token } });
        if (!r.ok) throw new Error("No se han podido descargar los datos");
        const url = URL.createObjectURL(await r.blob());
        const a = Object.assign(document.createElement("a"), { href: url, download: "mis_datos_telerehab.json" });
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
      } catch (e) { aviso(e.message); }
    };
    hoja.querySelector("#p-retirar").onclick = async () => {
      if (!confirm("¿Seguro que quieres retirar tu consentimiento?")) return;
      try { await api("/api/consentimiento", { method: "DELETE" }); cerrarHoja(); inicio(pantallaConsentimiento); }
      catch (e) { aviso(e.message); }
    };
  });
}

// ─── Paciente ─────────────────────────────────────────────────────────────────
async function cargarEjercicios() {
  if (!S.ejercicios) S.ejercicios = await api("/api/ejercicios");
  return S.ejercicios;
}

function resumen(historial) {
  const dias = new Set(historial.map((s) => s.fecha.slice(0, 10)));
  const hace7 = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  const hace30 = new Date(Date.now() - 30 * 864e5).toISOString().slice(0, 10);
  const reps = historial.reduce((a, s) => a + s.repeticiones, 0);
  const errs = historial.reduce((a, s) => a + Math.min(s.errores, s.repeticiones), 0);
  return {
    series: historial.length,
    dias: dias.size,
    semana: historial.filter((s) => s.fecha.slice(0, 10) >= hace7).length,
    dias30: [...dias].filter((d) => d >= hace30).length,
    correcto: reps ? Math.round((100 * (reps - errs)) / reps) : null,
  };
}

function tabs(actual, opciones) {
  return `<nav class="tabs" style="--n:${opciones.length}">${opciones.map(([id, icono, texto]) =>
    `<button data-tab="${id}" ${id === actual ? 'aria-current="page"' : ""}><span>${icono}</span>${texto}</button>`).join("")}</nav>`;
}

async function pacienteInicio(tab) {
  pintar(`<div class="cargando">Cargando…</div>`);
  let lista, historial, plan;
  try { [lista, historial, plan] = await Promise.all([cargarEjercicios(), api("/api/mi-historial"), api("/api/mi-plan")]); }
  catch (e) { return pintar(`<div class="vacio">${esc(e.message)}</div>`); }
  S.plan = plan.plan;

  const r = resumen(historial);
  const cuenta = `<button class="btn-icono" id="cuenta" aria-label="Mi cuenta" title="Mi cuenta">👤</button>`;
  const pestañas = tabs(tab, [["hoy", "🏃", "Hoy"], ["progreso", "📈", "Mi progreso"]]);

  if (tab === "hoy") {
    const ultima = {};
    historial.forEach((s) => { ultima[s.ejercicio] ||= s.fecha; });
    const enPlan = new Set(plan.plan.map((p) => p.ejercicio));
    const pendientes = plan.plan.filter((p) => !p.completado_hoy).length;
    const itemEjercicio = (e) => `
          <button class="item" data-ej="${esc(e.nombre)}">
            <span class="emoji">${EMOJIS[e.nombre] || "🏃"}</span>
            <span class="txt"><b>${esc(nombreVisible(e.nombre))}</b>
              <small>${e.por_tiempo ? "30 segundos" : "10 repeticiones"} · ${ultima[e.nombre] ? "último: " + fechaCorta(ultima[e.nombre]) : "sin hacer aún"}</small></span>
            <span class="flecha">›</span>
          </button>`;
    const itemPlan = (p) => {
      const pct = Math.min(100, Math.round((100 * p.hechas_hoy) / p.series));
      return `<button class="item ${p.completado_hoy ? "hecho" : ""}" data-ej="${esc(p.ejercicio)}">
        <span class="emoji">${p.completado_hoy ? "✅" : EMOJIS[p.ejercicio] || "🏃"}</span>
        <span class="txt"><b>${esc(nombreVisible(p.ejercicio))}</b>
          <small>${Math.min(p.hechas_hoy, p.series)} de ${p.series} ${p.series === 1 ? "serie" : "series"} hoy · ${esc(p.nivel)}</small>
          <span class="progreso" aria-hidden="true"><i style="width:${pct}%"></i></span></span>
        <span class="flecha">›</span></button>`;
    };
    let saludo;
    if (!plan.plan.length) saludo = r.semana ? `Llevas ${r.semana} ${r.semana === 1 ? "serie" : "series"} esta semana. ¡Sigue así!` : "Elige un ejercicio para empezar tu sesión de hoy.";
    else if (!pendientes) saludo = "¡Plan de hoy completado! 🎉 Buen trabajo.";
    else saludo = `Hoy te ${pendientes === 1 ? "queda 1 ejercicio" : `quedan ${pendientes} ejercicios`} de tu plan.`;

    const bloquePlan = plan.plan.length ? `
        <div class="tarjeta semana">
          <div class="anillo" style="--p:${plan.adherencia ?? 0}"><b>${plan.adherencia ?? 0}%</b></div>
          <div><b>Tu semana</b><p>${plan.plan.reduce((a, p) => a + Math.min(p.hechas_semana, p.objetivo_semana), 0)} de ${plan.plan.reduce((a, p) => a + p.objetivo_semana, 0)} series del plan en los últimos 7 días</p></div>
        </div>
        <h3 class="seccion-tit">Tu plan de hoy</h3>
        <div class="lista">${plan.plan.map(itemPlan).join("")}</div>
        <h3 class="seccion-tit">Otros ejercicios</h3>
        <div class="lista">${lista.filter((e) => !enPlan.has(e.nombre)).map(itemEjercicio).join("")}</div>`
      : `<div class="kpis">
          <div class="kpi"><b>${r.semana}</b><span>series esta semana</span></div>
          <div class="kpi"><b>${r.dias}</b><span>días entrenados</span></div>
          <div class="kpi"><b>${r.correcto ?? "–"}${r.correcto != null ? "%" : ""}</b><span>ejecución correcta</span></div>
        </div>
        <h3 class="seccion-tit">Tus ejercicios</h3>
        <div class="lista">${lista.map(itemEjercicio).join("")}</div>`;

    pintar(`<main class="pantalla">${cabecera("TeleRehab", { atras: false, derecha: cuenta })}
      <div class="contenido">
        <div class="saludo"><h2>Hola, ${esc(S.usuario.nombre)} 👋</h2><p>${saludo}</p></div>
        ${bloquePlan}
      </div>${pestañas}</main>`, () => {
      app.querySelectorAll("[data-ej]").forEach((b) => (b.onclick = () => ir(() => detalleEjercicio(b.dataset.ej))));
    });
  } else {
    const hechos = lista.filter((e) => historial.some((s) => s.ejercicio === e.nombre));
    pintar(`<main class="pantalla">${cabecera("Mi progreso", { atras: false, derecha: cuenta })}
      <div class="contenido">
        <div class="kpis" style="margin-top:6px">
          <div class="kpi"><b>${r.series}</b><span>series totales</span></div>
          <div class="kpi"><b>${r.dias30}</b><span>días (últimos 30)</span></div>
          <div class="kpi"><b>${r.correcto ?? "–"}${r.correcto != null ? "%" : ""}</b><span>ejecución correcta</span></div>
        </div>
        ${hechos.length ? bloqueProgreso(hechos.map((e) => e.nombre), historial, (ej) => `/api/mi-progreso.png?ejercicio=${encodeURIComponent(ej)}&token=${S.token}`)
        : `<div class="vacio"><span class="emoji">📊</span>Cuando completes tu primera serie verás aquí tu evolución.</div>`}
      </div>${pestañas}</main>`, () => activarProgreso());
  }
  document.getElementById("cuenta").onclick = hojaCuentaPaciente;
  app.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => ir(() => pacienteInicio(b.dataset.tab), { reemplazar: true })));
}

/* Gráfica + lista por días de un ejercicio, con chips para cambiar de ejercicio. */
function bloqueProgreso(nombres, historial, urlGrafica) {
  const html = `<h3 class="seccion-tit">Evolución por ejercicio</h3>
    <div class="chips" role="group" aria-label="Ejercicio">${nombres.map((n, i) =>
    `<button class="chip" data-chip="${esc(n)}" aria-pressed="${i === 0}">${esc(nombreVisible(n))}</button>`).join("")}</div>
    <div id="zona-progreso"></div>`;
  bloqueProgreso.ctx = { historial, urlGrafica };
  return html;
}
function activarProgreso() {
  const chips = app.querySelectorAll("[data-chip]");
  if (!chips.length) return;
  const mostrar = (ej) => {
    chips.forEach((c) => c.setAttribute("aria-pressed", c.dataset.chip === ej));
    const { historial, urlGrafica } = bloqueProgreso.ctx;
    const series = historial.filter((s) => s.ejercicio === ej);
    const porDia = {};
    series.forEach((s) => (porDia[s.fecha.slice(0, 10)] ||= []).unshift(s));
    const unidad = (n) => esPorTiempo(ej) ? "s" : (n === 1 ? " rep" : " reps");
    document.getElementById("zona-progreso").innerHTML = `
      <img class="grafica" alt="Gráfica de evolución de ${esc(nombreVisible(ej))}" src="${urlGrafica(ej)}">
      <h3 class="seccion-tit">Historial</h3>
      <div class="lista">${Object.keys(porDia).sort().reverse().slice(0, 30).map((d) => `
        <div class="tarjeta dia"><h3>${fechaCorta(d)} <span class="etiqueta">${porDia[d].length} ${porDia[d].length === 1 ? "serie" : "series"}</span></h3>
          ${porDia[d].map((s, i) => `<div class="serie"><span>Serie ${i + 1} · ${esc(s.nivel)}</span>
            <span class="etiqueta ${s.errores ? "mal" : "ok"}">${s.repeticiones}${unidad(s.repeticiones)} · ${s.errores} ${s.errores === 1 ? "error" : "errores"}</span></div>`).join("")}
        </div>`).join("")}</div>`;
  };
  chips.forEach((c) => (c.onclick = () => mostrar(c.dataset.chip)));
  mostrar(chips[0].dataset.chip);
}

async function detalleEjercicio(nombre, mensajeError) {
  const ej = (await cargarEjercicios()).find((e) => e.nombre === nombre);
  const recetado = (S.plan || []).find((p) => p.ejercicio === nombre);
  // Si el fisio lo ha recetado, se empieza en su nivel; si no, en el último que eligió el paciente
  let nivel = (recetado && recetado.nivel) || leer("nivel:" + nombre) || "principiante";
  pintar(`<main class="pantalla">${cabecera(nombreVisible(nombre))}
    <div class="contenido sin-tabs">
      ${mensajeError ? `<div class="alerta">⚠️ ${esc(mensajeError)}</div>` : ""}
      ${recetado ? `<div class="tarjeta" style="margin-bottom:14px"><b>📋 Recetado por tu fisioterapeuta</b>
        <p class="receta" style="margin-top:4px">${recetado.series} ${recetado.series === 1 ? "serie" : "series"} al día · ${recetado.dias_semana} ${recetado.dias_semana === 1 ? "día" : "días"} por semana · nivel ${esc(recetado.nivel)}.
        Hoy llevas ${Math.min(recetado.hechas_hoy, recetado.series)} de ${recetado.series}.</p></div>` : ""}
      <video class="video-explicativo" src="${ej.video}" controls playsinline preload="metadata" ${mensajeError ? "autoplay" : ""}></video>
      <h3 class="seccion-tit">Antes de empezar</h3>
      <ul class="consejos">${ej.consejos.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
      <h3 class="seccion-tit">Nivel</h3>
      <div class="segmentado" role="group" aria-label="Nivel">${NIVELES.map(([id, txt]) =>
    `<button data-nivel="${id}" aria-pressed="${id === nivel}">${txt}</button>`).join("")}</div>
      <div class="pie-fijo"><button class="btn" id="empezar">▶ Empezar serie</button></div>
    </div></main>`, () => {
    app.querySelectorAll("[data-nivel]").forEach((b) => (b.onclick = () => {
      nivel = b.dataset.nivel; guardar("nivel:" + nombre, nivel);
      app.querySelectorAll("[data-nivel]").forEach((x) => x.setAttribute("aria-pressed", x === b));
    }));
    document.getElementById("empezar").onclick = () => elegirFuente(ej, nivel);
  });
}

function elegirFuente(ej, nivel) {
  const hayCamara = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  abrirHoja(`<h2>¿Cómo quieres hacer la serie?</h2>
    <div class="lista">
      ${hayCamara ? `
      <button class="item" data-fuente="user"><span class="emoji">🤳</span><span class="txt"><b>Cámara frontal</b><small>Apoya el móvil y ponte delante</small></span><span class="flecha">›</span></button>
      <button class="item" data-fuente="environment"><span class="emoji">📷</span><span class="txt"><b>Cámara trasera</b><small>Si otra persona te graba</small></span><span class="flecha">›</span></button>`
      : `<div class="alerta">Para usar la cámara abre la app con <b>https</b> o desde este mismo ordenador (localhost).</div>`}
      <button class="item" data-fuente="archivo"><span class="emoji">🎞️</span><span class="txt"><b>Analizar un vídeo</b><small>Un vídeo grabado de tu ejercicio</small></span><span class="flecha">›</span></button>
      <button class="item" data-fuente="ejemplo"><span class="emoji">🎬</span><span class="txt"><b>Probar con el vídeo de ejemplo</b><small>Demostración: analiza el vídeo explicativo</small></span><span class="flecha">›</span></button>
    </div>
    <input type="file" id="archivo" accept="video/*" hidden>
    <button class="btn fantasma" data-cerrar style="margin-top:8px">Cancelar</button>`, (hoja) => {
    const input = hoja.querySelector("#archivo");
    input.onchange = () => input.files[0] && ir(() => serieDirecto(ej, nivel, { tipo: "video", url: URL.createObjectURL(input.files[0]) }));
    hoja.querySelectorAll("[data-fuente]").forEach((b) => (b.onclick = () => {
      const f = b.dataset.fuente;
      if (f === "archivo") return input.click();
      if (f === "ejemplo") return ir(() => serieDirecto(ej, nivel, { tipo: "video", url: ej.video }));
      ir(() => serieDirecto(ej, nivel, { tipo: "camara", modo: f }));
    }));
  });
}

// ─── Serie en directo ─────────────────────────────────────────────────────────
let limpiezaDirecto = null;

async function serieDirecto(ej, nivel, fuente) {
  pintar(`<div class="directo">
    <div class="barra-sup">
      <button class="btn-icono" id="cerrar" aria-label="Detener y salir">✕</button>
      <h2>${esc(nombreVisible(ej.nombre))} · ${esc(nivel)}</h2>
      <span class="pildora" id="errores">0/3 errores</span>
    </div>
    <div class="lienzo">
      <video id="entrada" class="oculto" playsinline muted></video>
      <img id="salida" alt="Vista de la cámara con el análisis de tu postura">
      <div class="mensaje" id="mensaje">Preparando la cámara…</div>
    </div>
    <div class="barra-inf">
      <button class="btn peligro" id="detener">■ Terminar serie</button>
    </div></div>`);

  const video = document.getElementById("entrada");
  const salida = document.getElementById("salida");
  const mensaje = document.getElementById("mensaje");
  const pildora = document.getElementById("errores");
  const lienzo = document.createElement("canvas");
  const ctx = lienzo.getContext("2d");
  // Hasta 2 fotogramas en vuelo: el móvil prepara el siguiente mientras el servidor analiza el anterior
  const MAX_EN_VUELO = 2;
  let stream = null, ws = null, enVuelo = 0, terminado = false, urlPrevia = null, vivo = true;

  const limpiar = () => {
    vivo = false;
    stream && stream.getTracks().forEach((t) => t.stop());
    video.pause();
    if (ws && ws.readyState === 1 && !terminado) ws.send("stop");
    urlPrevia && URL.revokeObjectURL(urlPrevia);
    limpiezaDirecto = null;
  };
  limpiezaDirecto = limpiar;

  const terminar = () => {
    if (terminado) return;
    terminado = true;
    mensaje.textContent = "Guardando la serie…";
    if (ws && ws.readyState === 1) ws.send("stop");
  };
  document.getElementById("detener").onclick = terminar;
  document.getElementById("cerrar").onclick = terminar;

  try {
    if (fuente.tipo === "camara") {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false, video: { facingMode: fuente.modo, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      video.srcObject = stream;
    } else {
      video.src = fuente.url;
      video.onended = terminar;
    }
    await video.play();
  } catch (e) {
    limpiar();
    mensaje.textContent = fuente.tipo === "camara"
      ? "No se ha podido abrir la cámara. Revisa que la app tenga permiso para usarla."
      : "No se ha podido reproducir el vídeo.";
    document.getElementById("detener").textContent = "Volver";
    document.getElementById("detener").onclick = volver;
    document.getElementById("cerrar").onclick = volver;
    return;
  }
  if (!vivo) return;

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/serie?token=${encodeURIComponent(S.token)}&ejercicio=${encodeURIComponent(ej.nombre)}&nivel=${nivel}`);
  ws.binaryType = "arraybuffer";

  const enviar = () => {
    if (!vivo || terminado || enVuelo >= MAX_EN_VUELO || !ws || ws.readyState !== 1) return;
    if (!video.videoWidth) { setTimeout(enviar, 100); return; }  // la cámara aún no da imagen
    // 720 px de ancho (como una webcam HD): el marcador que dibuja cada módulo cabe también en vertical
    const escala = Math.min(1, 720 / video.videoWidth);
    lienzo.width = Math.round(video.videoWidth * escala);
    lienzo.height = Math.round(video.videoHeight * escala);
    ctx.drawImage(video, 0, 0, lienzo.width, lienzo.height);
    // toDataURL es síncrono (~20 ms); toBlob puede retrasarse mucho si el navegador está en segundo plano
    const datos = lienzo.toDataURL("image/jpeg", 0.72);
    const bin = atob(datos.slice(datos.indexOf(",") + 1));
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    ws.send(bytes);
    enVuelo++;
    queueMicrotask(enviar);
  };

  ws.onopen = () => { mensaje.textContent = ""; enviar(); };
  ws.onerror = () => { mensaje.textContent = "Se ha perdido la conexión con el servidor."; };
  ws.onmessage = (ev) => {
    if (!vivo) return;
    if (typeof ev.data !== "string") {
      const url = URL.createObjectURL(new Blob([ev.data], { type: "image/jpeg" }));
      salida.src = url; urlPrevia && URL.revokeObjectURL(urlPrevia); urlPrevia = url;
      return;
    }
    const d = JSON.parse(ev.data);
    if (d.estado === "guardado") {
      limpiar();
      return ir(() => resultadoSerie(ej, nivel, d.resultado), { reemplazar: true });
    }
    if (d.estado === "error") {
      terminado = true; limpiar(); mensaje.textContent = d.mensaje;
      const b = document.getElementById("detener");
      b.textContent = "Volver"; b.onclick = volver; document.getElementById("cerrar").onclick = volver;
      return;
    }
    pildora.textContent = `${d.errores}/3 errores`;
    pildora.classList.toggle("mal", d.errores > 0);
    if (d.estado === "completado" || d.estado === "cortafuegos") {
      terminado = true; mensaje.textContent = "Guardando la serie…"; return;
    }
    if (!terminado) mensaje.textContent = d.persona_detectada ? "" : "No te veo bien 👀 Colócate como indican los consejos.";
    enVuelo = Math.max(0, enVuelo - 1);
    queueMicrotask(enviar);
  };
}

function resultadoSerie(ej, nivel, resultado) {
  const textos = {
    completado: ["🎉", "¡Serie completada!", "Muy bien hecho. Tu fisioterapeuta ya puede ver el informe y el vídeo de la serie."],
    cortafuegos: ["⚠️", "Paramos para cuidarte", "Vuelve a ver el vídeo explicativo para mejorar la técnica en el ejercicio."],
    detenido: ["💾", "Serie guardada", "Has terminado la serie antes de tiempo. La hemos guardado igualmente."],
  };
  const [icono, titulo, texto] = textos[resultado] || textos.detenido;
  hablar(titulo);
  pintar(`<main class="pantalla resultado">
    <div class="grande">${icono}</div><h2>${titulo}</h2><p>${texto}</p>
    <div class="fila-btns">
      ${resultado === "cortafuegos"
      ? `<button class="btn" id="b1">🎬 Ver vídeo explicativo</button>`
      : `<button class="btn" id="b1">↻ Hacer otra serie</button>`}
      <button class="btn secundario" id="b2">Volver a mi plan</button>
    </div></main>`, () => {
    document.getElementById("b1").onclick = () => resultado === "cortafuegos"
      ? ir(() => detalleEjercicio(ej.nombre, texto), { reemplazar: true })
      : ir(() => detalleEjercicio(ej.nombre), { reemplazar: true });
    document.getElementById("b2").onclick = () => inicio(() => pacienteInicio("hoy"));
    // Progreso del plan de hoy en este ejercicio (si el fisio lo ha recetado)
    api("/api/mi-plan").then((p) => {
      S.plan = p.plan;
      const item = p.plan.find((x) => x.ejercicio === ej.nombre);
      if (!item) return;
      const linea = document.createElement("p");
      linea.className = "receta";
      linea.textContent = item.completado_hoy
        ? `✅ Has completado las ${item.series} series de hoy de ${nombreVisible(ej.nombre)}.`
        : `Llevas ${item.hechas_hoy} de ${item.series} series de hoy de ${nombreVisible(ej.nombre)}.`;
      document.querySelector(".resultado p")?.after(linea);
    }).catch(() => { });
  });
}

// ─── Fisioterapeuta ───────────────────────────────────────────────────────────
async function fisioInicio() {
  pintar(`<div class="cargando">Cargando…</div>`);
  let pacientes;
  try { pacientes = await api("/api/fisio/pacientes"); } catch (e) { return pintar(`<div class="vacio">${esc(e.message)}</div>`); }
  const ajustes = `<button class="btn-icono" id="ajustes" aria-label="Ajustes">⚙︎</button>`;
  const activos = pacientes.filter((p) => p.ultima && p.ultima.slice(0, 10) >= new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10)).length;
  const conPlan = pacientes.filter((p) => p.adherencia != null);
  const adhMedia = conPlan.length ? Math.round(conPlan.reduce((a, p) => a + p.adherencia, 0) / conPlan.length) : null;
  // Pacientes que necesitan que el fisio haga algo (alertas graves o medias), los más urgentes primero
  const urgencia = (p) => (p.alertas.some((a) => a.gravedad === "alta") ? 0 : p.alertas.some((a) => a.gravedad === "media") ? 1 : 2);
  const atencion = pacientes.filter((p) => urgencia(p) < 2).sort((a, b) => urgencia(a) - urgencia(b));
  pintar(`<main class="pantalla">${cabecera("Mis pacientes", { atras: false, derecha: ajustes })}
    <div class="contenido sin-tabs">
      <div class="kpis" style="margin:6px 0 4px">
        <div class="kpi"><b>${pacientes.length}</b><span>pacientes</span></div>
        <div class="kpi"><b>${activos}</b><span>activos esta semana</span></div>
        <div class="kpi"><b>${adhMedia ?? "–"}${adhMedia != null ? "%" : ""}</b><span>adherencia media al plan</span></div>
      </div>
      ${atencion.length ? `<h3 class="seccion-tit">Requieren atención (${atencion.length})</h3>
      <div class="atencion">${atencion.slice(0, 5).map((p) => {
        const a = p.alertas.find((x) => x.gravedad !== "info");
        return `<button class="aviso-pac ${a.gravedad}" data-pac="${p.id}"><span class="punto"></span>
          <span class="txt"><b>${esc(p.nombre)}</b><span>${esc(a.texto)}${p.alertas.filter((x) => x.gravedad !== "info").length > 1 ? " · y más" : ""}</span></span>
          <span class="flecha">›</span></button>`;
      }).join("")}</div>` : ""}
      <h3 class="seccion-tit">Todos</h3>
      <input class="buscador" id="buscar" type="search" placeholder="🔍  Buscar paciente" aria-label="Buscar paciente">
      <div class="lista" id="lista"></div>
      <div class="pie-fijo"><button class="btn" id="nuevo">＋ Nuevo paciente</button></div>
    </div></main>`, () => {
    const pintarLista = (filtro = "") => {
      const f = filtro.trim().toLowerCase();
      const visibles = pacientes.filter((p) => p.nombre.toLowerCase().includes(f));
      document.getElementById("lista").innerHTML = visibles.length ? visibles.map((p) => `
        <button class="item" data-pac="${p.id}">
          <span class="emoji">${esc(p.nombre.slice(0, 1).toUpperCase())}</span>
          <span class="txt"><b>${esc(p.nombre)}</b>
            <small>${p.edad ? p.edad + " años · " : ""}${p.series} series · ${p.ultima ? "última: " + fechaCorta(p.ultima) : "sin sesiones"}</small></span>
          ${etiquetaAdherencia(p.adherencia)}</button>`).join("")
        : `<div class="vacio"><span class="emoji">🧑‍⚕️</span>${pacientes.length ? "Ningún paciente coincide." : "Aún no tienes pacientes. Da de alta el primero."}</div>`;
      app.querySelectorAll("[data-pac]").forEach((b) => (b.onclick = () => ir(() => fisioPaciente(+b.dataset.pac, "plan"))));
    };
    pintarLista();
    document.getElementById("buscar").oninput = (e) => pintarLista(e.target.value);
    document.getElementById("nuevo").onclick = hojaNuevoPaciente;
    document.getElementById("ajustes").onclick = hojaAjustesFisio;
  });
}

function etiquetaAdherencia(adh) {
  if (adh == null) return `<span class="adh" title="Sin plan asignado">sin plan</span>`;
  const clase = adh >= 80 ? "ok" : adh >= 50 ? "media" : "baja";
  return `<span class="adh ${clase}" title="Adherencia al plan (7 días)">${adh}%</span>`;
}

function hojaNuevoPaciente() {
  abrirHoja(`<h2>Nuevo paciente</h2>
    <form id="f-nuevo" novalidate>
      <div class="campo"><label for="n-nombre">Nombre (será su usuario)</label><input id="n-nombre" autocapitalize="words" required></div>
      <div class="campo"><label for="n-edad">Edad</label><input id="n-edad" inputmode="numeric" pattern="[0-9]*"></div>
      <div class="campo"><label for="n-notas">Lesión / notas</label><textarea id="n-notas" placeholder="p. ej. Prótesis de rodilla derecha"></textarea></div>
      <div class="dos-col">
        <div class="campo"><label for="n-p1">Contraseña</label><input id="n-p1" type="password" autocomplete="new-password"></div>
        <div class="campo"><label for="n-p2">Repetir</label><input id="n-p2" type="password" autocomplete="new-password"></div>
      </div>
      <p class="error" id="n-err"></p>
      <div class="fila-btns"><button class="btn" type="submit">Dar de alta</button>
      <button class="btn fantasma" type="button" data-cerrar>Cancelar</button></div>
    </form>`, (hoja) => {
    hoja.querySelector("#f-nuevo").onsubmit = async (e) => {
      e.preventDefault();
      const v = (id) => hoja.querySelector(id).value;
      try {
        const r = await api("/api/fisio/pacientes", {
          method: "POST", body: JSON.stringify({
            nombre: v("#n-nombre"), edad: v("#n-edad"), notas: v("#n-notas"), password: v("#n-p1"), password2: v("#n-p2"),
          }),
        });
        cerrarHoja(); aviso(`✅ ${r.nombre} dado de alta. Ahora asígnale su plan.`);
        ir(() => fisioPaciente(r.id, "plan"));
      } catch (err) { hoja.querySelector("#n-err").textContent = err.message; }
    };
  });
}

function hojaAjustesFisio() {
  abrirHoja(`<h2>Ajustes</h2>
    <form id="f-pass" novalidate>
      <div class="campo"><label for="a-act">Contraseña actual</label><input id="a-act" type="password" autocomplete="current-password"></div>
      <div class="dos-col">
        <div class="campo"><label for="a-n1">Nueva</label><input id="a-n1" type="password" autocomplete="new-password"></div>
        <div class="campo"><label for="a-n2">Repetir</label><input id="a-n2" type="password" autocomplete="new-password"></div>
      </div>
      <p class="error" id="a-err"></p>
      <div class="fila-btns">
        <button class="btn" type="submit">🔑 Cambiar contraseña</button>
        <button class="btn secundario" type="button" id="salir">Cerrar sesión</button>
      </div>
    </form>`, (hoja) => {
    hoja.querySelector("#salir").onclick = () => { cerrarHoja(); cerrarSesion(); };
    hoja.querySelector("#f-pass").onsubmit = async (e) => {
      e.preventDefault();
      const v = (id) => hoja.querySelector(id).value;
      try {
        await api("/api/fisio/password", { method: "POST", body: JSON.stringify({ actual: v("#a-act"), nueva: v("#a-n1"), nueva2: v("#a-n2") }) });
        cerrarHoja(); aviso("✅ Contraseña cambiada");
      } catch (err) { hoja.querySelector("#a-err").textContent = err.message; }
    };
  });
}

async function fisioPaciente(id, tab) {
  pintar(`<div class="cargando">Cargando…</div>`);
  let datos;
  try { datos = await api(`/api/fisio/pacientes/${id}/historial`); } catch (e) { return pintar(`<div class="vacio">${esc(e.message)}</div>`); }
  const { nombre, sesiones } = datos;
  const r = resumen(sesiones);
  const pestañas = tabs(tab, [["plan", "📋", "Plan"], ["progreso", "📈", "Progreso"], ["sesiones", "🗓️", "Sesiones"]]);
  const vacio = `<div class="vacio"><span class="emoji">🗓️</span>${esc(nombre)} todavía no tiene entrenamientos registrados.</div>`;
  let cuerpo;

  if (tab === "plan") {
    return fisioPlan(id, datos, pestañas);
  } else if (tab === "progreso") {
    const nombresEj = [...new Set(sesiones.map((s) => s.ejercicio))];
    cuerpo = `<div class="kpis" style="margin-top:6px">
        <div class="kpi"><b>${r.series}</b><span>series</span></div>
        <div class="kpi"><b>${r.dias30}</b><span>días (últ. 30)</span></div>
        <div class="kpi"><b>${r.correcto ?? "–"}${r.correcto != null ? "%" : ""}</b><span>correcto</span></div>
      </div>
      ${sesiones.length ? bloqueProgreso(nombresEj, sesiones, (ej) => `/api/fisio/pacientes/${id}/progreso.png?ejercicio=${encodeURIComponent(ej)}&token=${S.token}`) : vacio}`;
  } else {
    const porDia = {};
    sesiones.forEach((s) => (porDia[s.fecha.slice(0, 10)] ||= []).unshift(s));
    cuerpo = sesiones.length ? `<div class="lista" style="margin-top:6px">${Object.keys(porDia).sort().reverse().map((d) => {
      const porEj = {};
      porDia[d].forEach((s) => (porEj[s.ejercicio] ||= []).push(s));
      return `<div class="tarjeta dia"><h3>📅 ${fechaCorta(d)} <span class="etiqueta">${porDia[d].length} ${porDia[d].length === 1 ? "serie" : "series"}</span></h3>
        ${Object.entries(porEj).map(([ej, lista]) => lista.map((s, i) => `
          <div class="serie"><span><b>${esc(nombreVisible(ej))}</b> · serie ${i + 1}<br>
            <small class="etiqueta ${s.errores ? "mal" : "ok"}">${s.repeticiones}${esPorTiempo(ej) ? "s" : (s.repeticiones === 1 ? " rep" : " reps")} · ${s.errores} ${s.errores === 1 ? "error" : "errores"} · ${esc(s.nivel)}</small></span>
            <button data-serie='${esc(JSON.stringify({ fecha: d, ejercicio: ej, idx: i, ts: s.fecha }))}'>Informe</button></div>`).join("")).join("")}
      </div>`;
    }).join("")}</div>` : vacio;
  }

  pintar(`<main class="pantalla">${cabecera(nombre)}<div class="contenido">${cuerpo}</div>${pestañas}</main>`, () => {
    activarProgreso();
    app.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => ir(() => fisioPaciente(id, b.dataset.tab), { reemplazar: true })));
    app.querySelectorAll("[data-serie]").forEach((b) => (b.onclick = () => hojaSerie(id, JSON.parse(b.dataset.serie))));
  });
}

/* Pestaña "Plan" del paciente: adherencia, alertas, editor del plan y protección de datos. */
async function fisioPlan(id, datos, pestañas) {
  const lista = await cargarEjercicios();
  const { nombre, plan, adherencia, alertas, consentimiento } = datos;
  // Estado editable: un registro por ejercicio del catálogo
  const estado = {};
  lista.forEach((e) => (estado[e.nombre] = { activo: false, nivel: "principiante", series: 3, dias_semana: 3 }));
  plan.forEach((p) => (estado[p.ejercicio] = { activo: true, nivel: p.nivel, series: p.series, dias_semana: p.dias_semana }));
  const porEj = Object.fromEntries(plan.map((p) => [p.ejercicio, p]));

  const contador = (ej, campo, txt, max) => `<div class="contador"><span>${txt}</span>
    <span class="ctrl"><button type="button" data-menos="${esc(ej)}|${campo}" aria-label="Menos ${txt}">−</button>
    <output data-valor="${esc(ej)}|${campo}">${estado[ej][campo]}</output>
    <button type="button" data-mas="${esc(ej)}|${campo}|${max}" aria-label="Más ${txt}">+</button></span></div>`;

  const filas = lista.map((e) => {
    const s = estado[e.nombre], p = porEj[e.nombre];
    return `<div class="fila-plan ${s.activo ? "activa" : ""}" data-fila="${esc(e.nombre)}">
      <div class="cab"><span>${EMOJIS[e.nombre] || "🏃"}</span><b>${esc(nombreVisible(e.nombre))}
        ${p ? `<br><small class="receta" style="font-weight:400">${p.hechas_semana}/${p.objetivo_semana} series esta semana</small>` : ""}</b>
        <label class="interruptor"><input type="checkbox" data-activo="${esc(e.nombre)}" ${s.activo ? "checked" : ""} aria-label="Incluir ${esc(nombreVisible(e.nombre))} en el plan"><span></span></label></div>
      <div class="ajustes">
        <div class="segmentado peq" role="group" aria-label="Nivel">${NIVELES.map(([nid, txt]) =>
      `<button type="button" data-niv="${esc(e.nombre)}|${nid}" aria-pressed="${s.nivel === nid}">${txt}</button>`).join("")}</div>
        ${contador(e.nombre, "series", "Series al día", 10)}
        ${contador(e.nombre, "dias_semana", "Días por semana", 7)}
      </div></div>`;
  }).join("");

  const alertasReales = alertas.filter((a) => a.tipo !== "sin_plan");
  pintar(`<main class="pantalla">${cabecera(nombre)}<div class="contenido">
    ${plan.length ? `<div class="tarjeta semana" style="margin-top:6px">
      <div class="anillo" style="--p:${adherencia ?? 0}"><b>${adherencia ?? 0}%</b></div>
      <div><b>Adherencia al plan</b><p>Series hechas de las recetadas en los últimos 7 días</p></div></div>`
      : `<div class="alerta" style="margin-top:6px">📋 ${esc(nombre)} todavía no tiene plan. Activa los ejercicios que debe hacer y pulsa <b>Guardar plan</b>.</div>`}
    ${alertasReales.length ? `<h3 class="seccion-tit">Alertas</h3><div class="atencion">${alertasReales.map((a) =>
        `<div class="aviso-pac ${a.gravedad}"><span class="punto"></span><span class="txt">${esc(a.texto)}</span></div>`).join("")}</div>` : ""}
    <h3 class="seccion-tit">Ejercicios recetados</h3>
    <div class="lista">${filas}</div>
    <div class="pie-fijo" style="bottom:calc(70px + var(--seguro-abajo))"><button class="btn" id="guardar-plan">💾 Guardar plan</button></div>
    <div class="zona-peligro">
      <h3 class="seccion-tit" style="margin-top:0">Protección de datos</h3>
      <p>${consentimiento ? `Consentimiento ${consentimiento.vigente ? "aceptado" : "de una versión anterior, aceptado"} el ${fechaCorta(consentimiento.fecha)}.` : "El paciente aún no ha aceptado el consentimiento: se le pedirá al entrar en la app."}</p>
      <p>Borrar al paciente elimina para siempre sus sesiones, informes y vídeos (derecho de supresión).</p>
      <button class="btn borde-rojo" id="borrar">🗑 Borrar paciente y todos sus datos</button>
    </div>
  </div>${pestañas}</main>`, () => {
    const refrescar = (ej) => {
      const fila = app.querySelector(`[data-fila="${CSS.escape(ej)}"]`);
      fila.classList.toggle("activa", estado[ej].activo);
      fila.querySelectorAll("[data-niv]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.niv.split("|")[1] === estado[ej].nivel));
      fila.querySelectorAll("[data-valor]").forEach((o) => (o.textContent = estado[ej][o.dataset.valor.split("|")[1]]));
    };
    app.querySelectorAll("[data-activo]").forEach((c) => (c.onchange = () => { estado[c.dataset.activo].activo = c.checked; refrescar(c.dataset.activo); }));
    app.querySelectorAll("[data-niv]").forEach((b) => (b.onclick = () => { const [ej, n] = b.dataset.niv.split("|"); estado[ej].nivel = n; refrescar(ej); }));
    app.querySelectorAll("[data-menos]").forEach((b) => (b.onclick = () => { const [ej, c] = b.dataset.menos.split("|"); estado[ej][c] = Math.max(1, estado[ej][c] - 1); refrescar(ej); }));
    app.querySelectorAll("[data-mas]").forEach((b) => (b.onclick = () => { const [ej, c, max] = b.dataset.mas.split("|"); estado[ej][c] = Math.min(+max, estado[ej][c] + 1); refrescar(ej); }));
    document.getElementById("guardar-plan").onclick = async (ev) => {
      const items = lista.filter((e) => estado[e.nombre].activo).map((e) => ({ ejercicio: e.nombre, ...estado[e.nombre], activo: undefined }));
      ev.target.disabled = true;
      try {
        await api(`/api/fisio/pacientes/${id}/plan`, { method: "PUT", body: JSON.stringify({ plan: items }) });
        aviso(items.length ? `✅ Plan guardado: ${items.length} ${items.length === 1 ? "ejercicio" : "ejercicios"}` : "Plan vaciado");
        fisioPaciente(id, "plan");
      } catch (e) { aviso(e.message); ev.target.disabled = false; }
    };
    document.getElementById("borrar").onclick = () => hojaBorrarPaciente(id, nombre);
    app.querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => ir(() => fisioPaciente(id, b.dataset.tab), { reemplazar: true })));
  });
}

function hojaBorrarPaciente(id, nombre) {
  abrirHoja(`<h2>Borrar a ${esc(nombre)}</h2>
    <p class="privacidad-txt">Se borrarán <b>para siempre</b> su cuenta, sus sesiones, su plan, sus informes y sus vídeos. No se puede deshacer.</p>
    <form id="f-borrar" novalidate>
      <div class="campo"><label for="b-nombre">Escribe <b>${esc(nombre)}</b> para confirmar</label><input id="b-nombre" autocomplete="off"></div>
      <p class="error" id="b-err"></p>
      <div class="fila-btns"><button class="btn peligro" type="submit">Borrar definitivamente</button>
        <button class="btn fantasma" type="button" data-cerrar>Cancelar</button></div>
    </form>`, (hoja) => {
    hoja.querySelector("#f-borrar").onsubmit = async (e) => {
      e.preventDefault();
      try {
        await api(`/api/fisio/pacientes/${id}`, { method: "DELETE", body: JSON.stringify({ confirmacion: hoja.querySelector("#b-nombre").value }) });
        cerrarHoja(); aviso(`${nombre} y todos sus datos se han borrado`); inicio(() => fisioInicio());
      } catch (err) { hoja.querySelector("#b-err").textContent = err.message; }
    };
  });
}

async function hojaSerie(id, s) {
  abrirHoja(`<div class="cargando">Buscando informe…</div>`);
  try {
    const q = new URLSearchParams({ paciente_id: id, fecha: s.fecha, ejercicio: s.ejercicio, idx: s.idx, ts: s.ts });
    const r = await api(`/api/fisio/serie?${q}`);
    const urlVideo = r.video ? `/api/fisio/video?ruta=${encodeURIComponent(r.video)}&token=${S.token}` : null;
    abrirHoja(`<h2>${esc(nombreVisible(s.ejercicio))} · serie ${s.idx + 1}</h2>
      ${urlVideo ? `<video class="video-serie" src="${urlVideo}" controls playsinline preload="metadata"></video>`
        : `<div class="alerta">No hay vídeo disponible para esta serie.</div>`}
      <pre class="informe">${esc(r.informe || "No se encontró el informe en texto para esta serie.")}</pre>
      <button class="btn secundario" data-cerrar style="margin-top:14px">Cerrar</button>`);
  } catch (e) { abrirHoja(`<div class="vacio">${esc(e.message)}</div>`); }
}

// ─── Arranque ─────────────────────────────────────────────────────────────────
const sesion = leer("sesion");
if (sesion && sesion.token) {
  S.token = sesion.token; S.usuario = sesion;
  // Comprueba que la sesión sigue siendo válida (el servidor puede haberse reiniciado)
  api(sesion.rol === "fisio" ? "/api/fisio/pacientes" : "/api/consentimiento")
    .then((r) => (sesion.rol === "paciente" && !r.aceptado ? inicio(pantallaConsentimiento) : entrar()))
    .catch(() => inicio(pantallaLogin));
} else {
  inicio(pantallaLogin);
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => { });
