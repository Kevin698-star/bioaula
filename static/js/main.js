/**
 * BioAula · main.js
 * Punto de entrada: inicialización y exposición global de la API pública.
 */

import { state, loadPersistedData } from './state.js';
import { toast, switchView, switchMatTab, setGenerating, refreshStatsBadge, showApp, toggleStudentDetail } from './ui.js';
import { onDragOver, onDragLeave, onDrop, handleFiles } from './files.js';
import { generateAll, showQuizReadyBadge, regenerateQuiz, renderShareLink, copyShareLink, openStudentMode, showQR, loadTeacherQuizzes, selectTeacherQuiz } from './quiz-generator.js';
import { startQuiz, showStudyMaterial, retakeQuiz } from './quiz-player.js';
import { getToken, getUser, isAuthenticated, logout, fetchMe, login, register, hasRole, saveAuth } from './auth.js';
import { applyPermissions } from './permissions.js';
import { downloadReport } from './stats.js';
import { initAdmin, openCreateUserModal, editUser, deleteUser, saveUser, closeUserModal, onAdminFilter } from './admin.js';

// ── Inicialización ────────────────────────────────────────────────────────────

window.addEventListener('load', async () => {
  loadPersistedData();
  checkStudentMode();

  // Si tiene API key O si ya está autenticado, mostrar la aplicación principal
  if (state.apiKey || isAuthenticated()) {
    showApp();
  }

  if (state.quiz) {
    showQuizReadyBadge();
    showStudyMaterial();
  }

  refreshStatsBadge();
  initAdmin();

  const apikeyEdit = document.getElementById('apikey-edit');
  if (apikeyEdit) apikeyEdit.value = state.apiKey;

  initAuthUI();

  if (isAuthenticated() && (hasRole('profesor') || hasRole('admin'))) {
    loadTeacherQuizzes();
  }
});

// ── Modo estudiante desde URL ─────────────────────────────────────────────────

async function checkStudentMode() {
  const params    = new URLSearchParams(window.location.search);
  const mode      = params.get('mode');
  const quizParam = params.get('quiz') || params.get('data'); // data = alias legacy
  const pathMatch = window.location.pathname.match(/^\/quiz\/(\d+)/);
  let quizId = pathMatch ? parseInt(pathMatch[1]) : null;

  if (!mode && !quizId && !quizParam) return;

  if (quizId) {
    // Obtener quiz desde backend público de forma segura
    try {
      const res = await fetch(`/api/public/quizzes/${quizId}`);
      if (res.ok) {
        const data = await res.json();
        state.quiz = {
          topic: data.titulo,
          nivel: data.nivel,
          numQ: data.num_q,
          bankSize: data.bank_size,
          banco: data.banco,
          apoyo: data.apoyo || '',
          _id: data.id,
        };
        localStorage.setItem('bioaula_quiz', JSON.stringify(state.quiz));
      }
    } catch (_) {}
  } else if (quizParam) {
    // Fallback: quiz codificado en base64 en la URL
    try {
      const quiz = JSON.parse(decodeURIComponent(escape(atob(quizParam))));
      state.quiz = quiz;
      localStorage.setItem('bioaula_quiz', JSON.stringify(quiz));
    } catch (_) {}
  }

  if (!state.quiz) return;

  state.studentMode = true;

  document.getElementById('setup-screen').style.display = 'none';
  document.getElementById('app').style.display          = 'flex';

  ['tab-prof', 'tab-stats', 'tab-admin', 'tab-cfg'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  switchView('estudiante');
  showStudyMaterial();
}

// ── Gestión de API Key ────────────────────────────────────────────────────────

function saveApiKey() {
  const k = document.getElementById('apikey-input').value.trim();
  if (!k.startsWith('AIza')) { toast('API Key inválida. Debe empezar con AIza...', true); return; }
  state.apiKey = k;
  localStorage.setItem('bioaula_key', k);
  showApp();
  toast('¡Bienvenido a BioAula!');
}

function updateApiKey() {
  const k = document.getElementById('apikey-edit').value.trim();
  if (!k) return;
  state.apiKey = k;
  localStorage.setItem('bioaula_key', k);
  toast('API Key actualizada');
}

function clearResults() {
  if (!confirm('¿Borrar todos los resultados de estudiantes?')) return;
  state.results = [];
  localStorage.removeItem('bioaula_results');
  refreshStatsBadge();

  // Reimportar stats para limpiar la vista
  import('./stats.js').then(m => m.renderStats());
  toast('Resultados borrados');
}

function clearAll() {
  if (!confirm('¿Borrar todo?')) return;
  localStorage.clear();
  location.reload();
}

// ── Autenticación ─────────────────────────────────────────────────────────────

function initAuthUI() {
  const user = getUser();
  const nameEl = document.getElementById('nav-user-name');
  const loginLink = document.getElementById('nav-login-link');
  const registerLink = document.getElementById('nav-register-link');
  const sep = document.getElementById('nav-auth-sep');
  const logoutBtn = document.getElementById('nav-logout-btn');

  if (user) {
    nameEl.textContent = `${user.nombre} (${user.rol})`;
    nameEl.style.display = 'inline';
    loginLink.style.display = 'none';
    sep.style.display = 'none';
    registerLink.style.display = 'none';
    logoutBtn.style.display = 'inline';
    applyPermissions();
    if (user.rol === 'profesor' || user.rol === 'admin') {
      loadTeacherQuizzes();
    }
  } else {
    nameEl.style.display = 'none';
    loginLink.style.display = 'inline';
    sep.style.display = 'inline';
    registerLink.style.display = 'inline';
    logoutBtn.style.display = 'none';
  }

  // Verificar que el token siga siendo válido al cargar
  if (getToken()) {
    fetchMe().then(u => {
      if (!u && user) { initAuthUI(); }
    });
  }
}

// ── API pública global (usada por onclick en el HTML) ─────────────────────────

window.BioAula = {
  // Auth
  saveApiKey,
  updateApiKey,
  continueWithoutKey: () => showApp(),
  clearResults,
  clearAll,
  authLogin: login,
  authRegister: register,
  authLogout: logout,
  authUser: getUser,
  authHasRole: hasRole,

  // Navegación
  switchView,
  switchMatTab,
  toast,

  // Archivos
  onDragOver,
  onDragLeave,
  onDrop,
  handleFiles: e => handleFiles(e.files),

  // Generación y gestión docente
  generateAll,
  regenerateQuiz,
  copyShareLink,
  openStudentMode,
  showQR,
  renderShareLink,
  loadTeacherQuizzes,
  selectTeacherQuiz,

  // Quiz (estudiante)
  startQuiz,
  retakeQuiz,

  // UI
  toggleStudentDetail,

  // Reports
  downloadReport,

  // Admin
  openCreateUserModal,
  editUser,
  deleteUser,
  saveUser,
  closeUserModal,
  onAdminFilter,
};
