import { getUser, isAuthenticated, hasRole } from './auth.js';

export function applyPermissions() {
  const user = getUser();
  if (!user) return;

  if (user.rol === 'estudiante') {
    ['tab-prof', 'tab-stats', 'tab-admin', 'tab-cfg'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
    const estTab = document.getElementById('tab-est');
    if (estTab) estTab.style.display = 'flex';
  } else if (user.rol === 'profesor') {
    // El profesor debe tener acceso a crear pruebas, estadísticas, configuración y vista estudiante
    ['tab-prof', 'tab-stats', 'tab-cfg', 'tab-est'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'flex';
    });
    const adminTab = document.getElementById('tab-admin');
    if (adminTab) adminTab.style.display = 'none';
  } else if (user.rol === 'admin') {
    ['tab-prof', 'tab-stats', 'tab-cfg', 'tab-est', 'tab-admin'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'flex';
    });
  }
}

export function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

export function requireRole(...roles) {
  if (!requireAuth()) return false;
  if (!hasRole(...roles)) {
    window.location.href = '/';
    return false;
  }
  return true;
}
