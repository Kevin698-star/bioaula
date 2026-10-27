/**
 * BioAula · quiz-generator.js
 * Generación del banco de preguntas e interacción con el backend Flask.
 */

import { state, callGemini, saveQuiz } from './state.js';
import { toast, setGenerating, refreshStatsBadge } from './ui.js';
import { buildGeminiFileParts } from './files.js';
import { showStudyMaterial } from './quiz-player.js';
import { getToken } from './auth.js';

// ── Generar banco de preguntas + material de apoyo ────────────────────────────

export async function generateAll() {
  const topic      = document.getElementById('topic').value.trim();
  const matText    = document.getElementById('material-text').value.trim();
  const nivel      = document.getElementById('nivel').value;
  const numQ       = parseInt(document.getElementById('num-questions').value);
  const bankSize   = parseInt(document.getElementById('bank-size').value);
  const urls       = document.getElementById('urls').value.trim();

  if (!topic) { toast('Escribe el nombre del tema', true); return; }
  if (!matText && !urls && state.uploadedFiles.length === 0) {
    toast('Agrega material de estudio', true); return;
  }

  setGenerating(true);
  document.getElementById('prof-output').innerHTML = `
    <div class="loading-box">
      <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
      Indexando material con RAG y generando banco de ${bankSize} preguntas únicas con Gemini 2.5...
    </div>`;

  const extraParts = buildGeminiFileParts();

  // ── RAG: indexar material + recuperar contexto relevante ──────────────
  let ragContext = null;
  const docId = 'gen_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);
  const fullText = buildFullMaterialText(matText, state.uploadedFiles);

  if (fullText.trim().length > 100) {
    try {
      const indexRes = await fetch('/api/rag/index-document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId, text: fullText }),
      });
      if (indexRes.ok) {
        const searchRes = await fetch('/api/rag/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document_id: docId, query: topic }),
        });
        if (searchRes.ok) {
          const { context } = await searchRes.json();
          if (context && context.length > 0) {
            ragContext = context;
          }
        }
      }
    } catch (_) {
      // Fallback silencioso al material completo
    }
  }

  // Usar contexto RAG si está disponible, si no el texto completo
  const effectiveMaterial = ragContext || matText;
  if (ragContext) {
    console.log(`RAG: ${fullText.length} → ${ragContext.length} caracteres (${Math.round((1 - ragContext.length / fullText.length) * 100)}% menos)`);
  }

  // Pedir prompts al servidor Flask con el material reducido
  let quizPrompt, quizSystem, apoyoPrompt, apoyoSystem;
  try {
    const res = await fetch('/api/build-prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, nivel, numQ, bankSize, materialText: effectiveMaterial, urls }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error del servidor');
    quizPrompt   = data.quizPrompt;
    quizSystem   = data.quizSystem;
    apoyoPrompt  = data.apoyoPrompt;
    apoyoSystem  = data.apoyoSystem;
  } catch (e) {
    setGenerating(false);
    toast('Error al preparar prompts: ' + e.message, true);
    return;
  }

  try {
    const [quizRaw, apoyoText] = await Promise.all([
      callGemini(quizPrompt, quizSystem, extraParts),
      callGemini(apoyoPrompt, apoyoSystem, extraParts),
    ]);

    const parsed = parseQuizJSON(quizRaw);
    if (!parsed || !Array.isArray(parsed.preguntas) || parsed.preguntas.length === 0) {
      console.error('Respuesta IA cruda:', quizRaw);
      throw new Error('No se encontraron preguntas en la respuesta. Intenta de nuevo.');
    }

    const quiz = { topic, nivel, numQ, bankSize, banco: parsed.preguntas, apoyo: apoyoText };
    saveQuiz(quiz);
    await saveQuizToBackend(quiz);

    showProfOutput();
    renderShareLink();
    showQuizReadyBadge();
    showStudyMaterial();
    toast(`¡Banco de ${parsed.preguntas.length} preguntas generado!`);
  } catch (e) {
    renderGenerationError(e);
    toast('Error: ' + e.message, true);
  }

  setGenerating(false);
}

// ── Parser robusto de JSON ────────────────────────────────────────────────────

export function parseQuizJSON(raw) {
  if (!raw) return null;

  // Estrategia 1: parseo directo
  try { return JSON.parse(raw.trim()); } catch (_) {}

  // Estrategia 2: limpiar backticks
  let clean = raw.replace(/^```+(?:json)?\s*/i, '').replace(/\s*```+$/i, '').trim();
  try { return JSON.parse(clean); } catch (_) {}

  // Estrategia 3: extraer objeto más grande
  const objMatch = clean.match(/\{[\s\S]*\}/);
  if (objMatch) { try { return JSON.parse(objMatch[0]); } catch (_) {} }

  // Estrategia 4: buscar array de preguntas directamente
  const arrMatch = clean.match(/"preguntas"\s*:\s*(\[[\s\S]*\])/);
  if (arrMatch) { try { return { preguntas: JSON.parse(arrMatch[1]) }; } catch (_) {} }

  // Estrategia 5: reparar JSON truncado
  const objStart = clean.indexOf('{');
  if (objStart !== -1) {
    let depth = 0, lastGoodEnd = -1;
    for (let i = objStart; i < clean.length; i++) {
      if (clean[i] === '{') depth++;
      else if (clean[i] === '}') { depth--; if (depth === 0) { lastGoodEnd = i; break; } }
    }
    if (lastGoodEnd !== -1) {
      try { return JSON.parse(clean.slice(objStart, lastGoodEnd + 1)); } catch (_) {}
    }
    const partial = clean.slice(objStart);
    for (const fix of [partial + ']}', partial + '"]}', partial + '"]}']) {
      try { const r = JSON.parse(fix); if (r.preguntas) return r; } catch (_) {}
    }
  }

  // Estrategia 6: extraer preguntas individuales
  const items = [];
  const re = /\{[^{}]*"pregunta"[^{}]*"opciones"[^{}]*"correcta"[^{}]*\}/g;
  let m;
  while ((m = re.exec(clean)) !== null) {
    try { items.push(JSON.parse(m[0])); } catch (_) {}
  }
  if (items.length > 0) return { preguntas: items };

  return null;
}

// ── Render del output del profesor ───────────────────────────────────────────

export function showProfOutput() {
  const q = state.quiz;
  const subtemas = [...new Set(q.banco.map(p => p.subtema).filter(Boolean))];

  document.getElementById('prof-output').innerHTML = `
    <div class="card" style="border-color:rgba(74,222,128,0.3)">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;flex-wrap:wrap;gap:8px">
        <div>
          <p style="font-family:'Syne',sans-serif;font-weight:700;font-size:15px;color:var(--accent)">${q.topic}</p>
          <p style="font-size:12px;color:var(--text3);margin-top:2px">Banco de ${q.banco.length} preguntas · ${q.numQ} por estudiante · Cada prueba es única</p>
        </div>
      </div>
      <p style="font-size:12px;color:var(--text3);margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;font-weight:500">Subtemas cubiertos</p>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1rem">
        ${subtemas.map(s => `<span style="font-size:11px;padding:3px 10px;border-radius:20px;background:rgba(74,222,128,0.1);color:var(--accent2);border:1px solid var(--border)">${s}</span>`).join('')}
      </div>
      <div class="divider"></div>
      <p style="font-size:12px;color:var(--text3);margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px;font-weight:500">Vista previa del banco</p>
      <div style="max-height:200px;overflow-y:auto">
        ${q.banco.slice(0, 8).map((p, i) => `
          <div style="font-size:13px;color:var(--text2);padding:5px 0;border-bottom:1px solid var(--border)">
            <span style="color:var(--text3);margin-right:8px">${i + 1}.</span>${p.pregunta}
          </div>`).join('')}
        ${q.banco.length > 8 ? `<div style="font-size:12px;color:var(--text3);padding:6px 0">... y ${q.banco.length - 8} preguntas más en el banco</div>` : ''}
      </div>
      <div class="btn-row">
        <button class="btn btn-primary btn-sm" onclick="window.BioAula.switchView('estudiante')">Probar como estudiante →</button>
        <button class="btn btn-sm" onclick="window.BioAula.regenerateQuiz()">Regenerar banco</button>
      </div>
    </div>

    <div class="card" style="border-color:rgba(96,165,250,0.35);background:rgba(96,165,250,0.04);margin-top:0">
      <div class="card-header" style="margin-bottom:0.75rem">
        <div class="card-icon" style="background:rgba(96,165,250,0.1)">🔗</div>
        <div>
          <div class="card-title" style="color:var(--blue)">Acceso para estudiantes</div>
          <div class="card-sub">Comparte este enlace o el código QR con tu clase</div>
        </div>
      </div>
      <p style="font-size:12px;color:var(--text3);margin-bottom:10px">
        Al abrir el enlace en otro dispositivo, el estudiante verá directamente el formulario de ingreso. El banco de preguntas viaja dentro del enlace.
      </p>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <div id="share-link-box" style="flex:1;min-width:200px;padding:8px 12px;background:var(--bg);border:1px solid var(--border2);border-radius:var(--radius-sm);font-size:12px;color:var(--accent2);word-break:break-all;font-family:monospace;max-height:56px;overflow:hidden">Generando enlace...</div>
        <button class="btn btn-sm" style="border-color:rgba(96,165,250,0.4);color:var(--blue);flex-shrink:0" onclick="window.BioAula.copyShareLink()">📋 Copiar</button>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-sm" onclick="window.BioAula.openStudentMode()" style="border-color:rgba(96,165,250,0.4);color:var(--blue)">🎓 Abrir vista estudiante</button>
        <button class="btn btn-sm" onclick="window.BioAula.showQR()" style="border-color:rgba(96,165,250,0.4);color:var(--blue)">📱 Ver código QR</button>
      </div>
      <div id="qr-container" style="display:none;margin-top:12px;text-align:center">
        <canvas id="qr-canvas" style="border-radius:var(--radius-sm);background:white;padding:8px"></canvas>
        <p style="font-size:11px;color:var(--text3);margin-top:6px">Escanea con la cámara del celular</p>
      </div>
    </div>`;
}

function renderGenerationError(e) {
  const msg      = e.message || '';
  const isQuota  = /quota|RESOURCE_EXHAUSTED|rate|429|free_tier/.test(msg);
  const isApiKey = /API_KEY|api key|401|403/.test(msg);
  const waitMatch = msg.match(/retry in ([\d.]+)s/i);
  const waitSecs  = waitMatch ? Math.ceil(parseFloat(waitMatch[1])) : null;

  let title, body, extra = '';

  if (isQuota) {
    title = '⏳ Cuota de Gemini agotada';
    body  = 'Has alcanzado el límite gratuito de la API de Gemini (20 solicitudes/día en el plan free).';
    extra = `
      <div style="margin:10px 0;padding:10px 14px;background:rgba(251,191,36,0.07);border:1px solid rgba(251,191,36,0.3);border-radius:var(--radius-sm);font-size:12px;color:#fde68a;line-height:1.6">
        <strong>¿Qué puedo hacer?</strong><br>
        • Espera ${waitSecs ? `<strong>~${waitSecs} segundos</strong> y vuelve a intentar` : 'unos minutos'}<br>
        • O activa facturación en <a href="https://aistudio.google.com" target="_blank" style="color:var(--accent)">aistudio.google.com</a>
      </div>
      ${waitSecs ? `<div id="quota-countdown" style="font-size:12px;color:var(--text3);margin-bottom:10px">Reintento automático en <strong id="countdown-num">${waitSecs}</strong>s...</div>` : ''}`;
  } else if (isApiKey) {
    title = '🔑 API Key inválida o sin permisos';
    body  = 'Verifica tu API Key en ⚙ Configuración.';
    extra = `<p style="font-size:12px;color:var(--text3);margin-bottom:10px">Ve a <a href="https://aistudio.google.com/apikey" target="_blank" style="color:var(--accent)">aistudio.google.com/apikey</a></p>`;
  } else {
    title = '⚠ Error al generar';
    body  = msg || 'Error desconocido. Verifica tu conexión y API Key.';
    extra = `<p style="font-size:12px;color:var(--text3);margin-bottom:10px">Si el problema persiste, reduce el banco de preguntas o el material.</p>`;
  }

  document.getElementById('prof-output').innerHTML = `
    <div class="card" style="border-color:rgba(248,113,113,0.3)">
      <p style="color:var(--danger);font-size:14px;font-weight:500;margin-bottom:6px">${title}</p>
      <p style="font-size:13px;color:var(--text2);margin-bottom:8px">${body}</p>
      ${extra}
      <button class="btn btn-primary btn-sm" id="retry-btn" onclick="window.BioAula.generateAll()">Reintentar →</button>
    </div>`;

  if (isQuota && waitSecs) {
    let remaining = waitSecs;
    const tick = setInterval(() => {
      remaining--;
      const cdEl  = document.getElementById('countdown-num');
      if (cdEl) cdEl.textContent = remaining;
      if (remaining <= 0) {
        clearInterval(tick);
        const cdBox = document.getElementById('quota-countdown');
        if (cdBox) cdBox.textContent = '¡Listo! Puedes reintentar ahora.';
        const btn = document.getElementById('retry-btn');
        if (btn) { btn.textContent = 'Reintentar ahora →'; btn.style.animation = 'pulse 1s infinite'; }
      }
    }, 1000);
  }
}

// ── Badge y estado del quiz ───────────────────────────────────────────────────

export function showQuizReadyBadge() {
  const b = document.getElementById('quiz-badge');
  if (b && state.quiz) b.style.display = 'inline';
}

export function regenerateQuiz() {
  if (!confirm('¿Regenerar el banco? Se perderá la prueba actual.')) return;
  state.quiz = null;
  localStorage.removeItem('bioaula_quiz');
  document.getElementById('prof-output').innerHTML = '';
  document.getElementById('quiz-badge').style.display = 'none';
  toast('Banco eliminado. Genera uno nuevo.');
}

// ── Share link ────────────────────────────────────────────────────────────────

export function buildShareLink() {
  const origin = window.location.origin;

  // Si la prueba tiene _id (guardada en backend), usar URL limpia
  if (state.quiz?._id) {
    return `${origin}/quiz/${state.quiz._id}`;
  }

  // Fallback: codificar todo el quiz en base64
  try {
    const quizData = btoa(unescape(encodeURIComponent(JSON.stringify(state.quiz))));
    return `${origin}/?mode=estudiante&quiz=${quizData}`;
  } catch (_) {
    return `${origin}/?mode=estudiante`;
  }
}

export function renderShareLink() {
  const el = document.getElementById('share-link-box');
  if (el) el.textContent = buildShareLink();
}

export function copyShareLink() {
  const link = buildShareLink();
  navigator.clipboard.writeText(link)
    .then(() => toast('¡Enlace copiado!'))
    .catch(() => {
      const ta = document.createElement('textarea');
      ta.value = link;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      toast('¡Enlace copiado!');
    });
}

export function openStudentMode() {
  window.open(buildShareLink(), '_blank');
}

export async function showQR() {
  const qrContainer = document.getElementById('qr-container');
  const canvas      = document.getElementById('qr-canvas');
  if (!qrContainer || !canvas) return;

  const visible = qrContainer.style.display !== 'none';
  if (visible) { qrContainer.style.display = 'none'; return; }
  qrContainer.style.display = 'block';

  try {
    if (!window.QRCode) {
      await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src     = 'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';
        s.onload  = res;
        s.onerror = rej;
        document.head.appendChild(s);
      });
    }
    canvas.innerHTML = '';
    const div  = document.createElement('div');
    qrContainer.appendChild(div);
    new QRCode(div, { text: buildShareLink(), width: 180, height: 180, colorDark: '#0a0f0d', colorLight: '#ffffff', correctLevel: QRCode.CorrectLevel.M });
    setTimeout(() => {
      const img = div.querySelector('img') || div.querySelector('canvas');
      if (img) { canvas.innerHTML = ''; canvas.appendChild(img); div.remove(); }
    }, 300);
  } catch (_) {
    qrContainer.innerHTML = `<p style="font-size:12px;color:var(--danger)">No se pudo generar el QR. Copia el enlace manualmente.</p>`;
  }
}

// ── Persistir prueba en el backend ────────────────────────────────────────────

// ── RAG: construir texto completo del material ────────────────────────────────

function buildFullMaterialText(matText, uploadedFiles) {
  const parts = [];
  if (matText) parts.push(matText);
  for (const f of uploadedFiles) {
    if (f.type === 'text' && f.content) {
      parts.push('[Archivo: ' + f.name + ']\n' + f.content);
    }
  }
  return parts.join('\n\n');
}

async function saveQuizToBackend(quiz) {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch('/api/quizzes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(quiz),
    });
    const data = await res.json();
    if (res.ok && data.quiz) {
      state.quiz._id = data.quiz.id;
      saveQuiz(state.quiz);
      loadTeacherQuizzes();
    }
  } catch (_) {
    // Silencio — la prueba ya se guardó localmente
  }
}

// ── Gestión de Evaluaciones Previas del Profesor ─────────────────────────────

export async function loadTeacherQuizzes() {
  const container = document.getElementById('my-quizzes-list');
  if (!container) return;

  const token = getToken();
  if (!token) {
    container.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:8px 0">Inicia sesión como profesor para ver tus evaluaciones guardadas en la nube.</p>';
    return;
  }

  container.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:8px 0">Cargando evaluaciones...</p>';

  try {
    const res = await fetch('/api/quizzes', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Error al obtener pruebas');
    const data = await res.json();
    const quizzes = data.quizzes || [];

    if (quizzes.length === 0) {
      container.innerHTML = '<p style="color:var(--text3);font-size:13px;padding:8px 0">No tienes evaluaciones guardadas aún. Crea tu primera prueba arriba.</p>';
      return;
    }

    container.innerHTML = quizzes.map(q => {
      const isCurrent = state.quiz?._id === q.id;
      const fecha = q.fecha_creacion
        ? new Date(q.fecha_creacion).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
        : '';
      return `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border:1px solid ${isCurrent ? 'var(--accent)' : 'var(--border)'};background:${isCurrent ? 'rgba(74,222,128,0.06)' : 'var(--surface)'};border-radius:var(--radius-sm);margin-bottom:8px;flex-wrap:wrap;gap:8px">
          <div>
            <div style="font-weight:600;font-size:14px;color:var(--text)">${q.titulo} ${isCurrent ? '<span style="font-size:10px;padding:2px 8px;border-radius:12px;background:var(--accent);color:var(--bg);margin-left:6px">Activa</span>' : ''}</div>
            <div style="font-size:12px;color:var(--text3);margin-top:2px">Nivel: ${q.nivel || 'N/A'} · ${q.bank_size || q.num_q || 0} preguntas · ${fecha}</div>
          </div>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm" onclick="window.BioAula.selectTeacherQuiz(${q.id})" ${isCurrent ? 'disabled' : ''}>
              ${isCurrent ? 'Cargada' : 'Seleccionar'}
            </button>
            <button class="btn btn-sm" onclick="navigator.clipboard.writeText('${window.location.origin}/quiz/${q.id}').then(() => window.BioAula.toast('¡Enlace copiado!'))">
              🔗
            </button>
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    container.innerHTML = `<p style="color:var(--danger);font-size:13px;padding:8px 0">Error al cargar evaluaciones: ${err.message}</p>`;
  }
}

export async function selectTeacherQuiz(quizId) {
  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`/api/quizzes/${quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('No se pudo cargar la prueba');
    const data = await res.json();
    const q = data.quiz;

    state.quiz = {
      topic: q.titulo,
      nivel: q.nivel,
      numQ: q.num_q,
      bankSize: q.bank_size,
      banco: q.banco,
      apoyo: q.apoyo || '',
      _id: q.id,
    };

    saveQuiz(state.quiz);
    showProfOutput();
    renderShareLink();
    showQuizReadyBadge();
    showStudyMaterial();
    loadTeacherQuizzes();
    toast(`Evaluación "${q.titulo}" activada`);
  } catch (err) {
    toast(err.message, true);
  }
}
