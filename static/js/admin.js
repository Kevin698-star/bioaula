/**
 * BioAula · admin.js
 * Panel administrativo — gestión de usuarios y dashboard.
 */

import { getToken, getUser } from './auth.js';
import { toast } from './ui.js';

// ── Estado local ──────────────────────────────────────────────────────────────

let editingUserId = null;

// ── Inicialización ────────────────────────────────────────────────────────────

export async function initAdmin() {
  const token = getToken();
  if (!token) return;

  await Promise.all([loadDashboard(), loadUsers()]);
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

async function loadDashboard() {
  const token = getToken();
  try {
    const res = await fetch('/api/admin/dashboard', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) { throw new Error('Error al cargar dashboard'); }
    const data = await res.json();
    renderDashboard(data);
  } catch {
    document.getElementById('admin-dashboard').innerHTML =
      '<p style="color:var(--danger)">Error al cargar dashboard</p>';
  }
}

function renderDashboard(data) {
  document.getElementById('admin-dashboard').innerHTML = `
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-num" style="color:var(--blue)">${data.total_profesores}</div>
        <div class="stat-label">Profesores</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">${data.total_estudiantes}</div>
        <div class="stat-label">Estudiantes</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color:var(--warn)">${data.total_pruebas}</div>
        <div class="stat-label">Pruebas</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color:var(--danger)">${data.total_intentos}</div>
        <div class="stat-label">Intentos</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="stat-card">
        <div class="stat-num">${data.total_usuarios}</div>
        <div class="stat-label">Total usuarios</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="font-size:14px;font-weight:400;color:var(--text3)">—</div>
        <div class="stat-label">Próximamente más métricas</div>
      </div>
    </div>`;
}

// ── Listado de usuarios ───────────────────────────────────────────────────────

export async function loadUsers(search = '', rol = '') {
  const token = getToken();
  try {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (rol) params.append('rol', rol);
    const qs = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`/api/admin/users${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) { throw new Error('Error al cargar usuarios'); }
    const data = await res.json();
    renderUsers(data.users);
  } catch {
    const tbody = document.querySelector('#admin-users-table tbody');
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--danger);padding:2rem">Error al cargar usuarios</td></tr>';
    }
  }
}

export function onAdminFilter() {
  const search = document.getElementById('admin-search')?.value.trim() || '';
  const rol = document.getElementById('admin-filter-role')?.value || '';
  loadUsers(search, rol);
}

function renderUsers(users) {
  const currentUserId = getUser()?.id;

  const rows = users.map(u => {
    const fecha = u.fecha_creacion
      ? new Date(u.fecha_creacion).toLocaleDateString('es-CO', {
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit',
        })
      : '—';
    const rolClass = u.rol === 'admin' ? 'admin-badge' : u.rol === 'profesor' ? 'prof-badge' : 'est-badge';
    const isSelf = u.id === currentUserId;

    return `<tr>
      <td>${escHtml(u.nombre)}</td>
      <td>${escHtml(u.correo)}</td>
      <td><span class="role-badge ${rolClass}">${u.rol}</span></td>
      <td style="font-size:12px;color:var(--text3)">${fecha}</td>
      <td class="actions-cell">
        <button class="btn btn-sm" onclick="BioAula.editUser(${u.id})" ${isSelf ? 'title="Eres tú"' : ''}>
          ✎
        </button>
        <button class="btn btn-sm" style="color:var(--danger);border-color:rgba(248,113,113,0.3)"
          onclick="BioAula.deleteUser(${u.id})" ${isSelf ? 'disabled title="No puedes eliminarte"' : ''}>
          ✕
        </button>
      </td>
    </tr>`;
  }).join('');

  const tbody = document.querySelector('#admin-users-table tbody');
  if (tbody) {
    tbody.innerHTML = rows;
  }
}

function escHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ── Modal de usuario (crear / editar) ─────────────────────────────────────────

export function openCreateUserModal() {
  editingUserId = null;
  document.getElementById('admin-modal-title').textContent = 'Crear usuario';
  document.getElementById('admin-modal-name').value = '';
  document.getElementById('admin-modal-email').value = '';
  document.getElementById('admin-modal-password').value = '';
  document.getElementById('admin-modal-password').required = true;
  document.getElementById('admin-modal-role').value = 'estudiante';
  document.getElementById('admin-modal-error').textContent = '';
  document.getElementById('admin-modal-error').style.display = 'none';
  document.getElementById('admin-modal-overlay').classList.add('open');
}

export function editUser(userId) {
  editingUserId = userId;
  const token = getToken();
  if (!token) return;

  fetch(`/api/admin/users`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then(r => r.json())
    .then(data => {
      const user = data.users.find(u => u.id === userId);
      if (!user) { toast('Usuario no encontrado', true); return; }

      document.getElementById('admin-modal-title').textContent = 'Editar usuario';
      document.getElementById('admin-modal-name').value = user.nombre;
      document.getElementById('admin-modal-email').value = user.correo;
      document.getElementById('admin-modal-password').value = '';
      document.getElementById('admin-modal-password').required = false;
      document.getElementById('admin-modal-password').placeholder = 'Dejar vacío para no cambiar';
      document.getElementById('admin-modal-role').value = user.rol;
      document.getElementById('admin-modal-error').textContent = '';
      document.getElementById('admin-modal-error').style.display = 'none';
      document.getElementById('admin-modal-overlay').classList.add('open');
    })
    .catch(() => toast('Error al cargar usuario', true));
}

export function closeUserModal() {
  editingUserId = null;
  document.getElementById('admin-modal-overlay').classList.remove('open');
}

export async function saveUser() {
  const token = getToken();
  if (!token) return;

  const name = document.getElementById('admin-modal-name').value.trim();
  const email = document.getElementById('admin-modal-email').value.trim();
  const password = document.getElementById('admin-modal-password').value;
  const role = document.getElementById('admin-modal-role').value;
  const errorEl = document.getElementById('admin-modal-error');

  if (!name) { showModalError('El nombre es requerido'); return; }
  if (!email || !email.includes('@')) { showModalError('Correo inválido'); return; }

  const body = { nombre: name, correo: email, rol: role };
  if (password) body.password = password;

  if (!editingUserId && !password) {
    showModalError('La contraseña es requerida (mín. 8 caracteres)');
    return;
  }
  if (password && password.length < 8) {
    showModalError('La contraseña debe tener al menos 8 caracteres');
    return;
  }

  try {
    const url = editingUserId
      ? `/api/admin/users/${editingUserId}`
      : '/api/admin/users';
    const method = editingUserId ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      showModalError(data.error || 'Error al guardar usuario');
      return;
    }

    toast(editingUserId ? 'Usuario actualizado' : 'Usuario creado');
    closeUserModal();
    loadUsers();
    loadDashboard();
  } catch {
    showModalError('Error de conexión');
  }
}

export async function deleteUser(userId) {
  if (!confirm('¿Eliminar este usuario definitivamente?')) return;

  const token = getToken();
  if (!token) return;

  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Error al eliminar', true); return; }

    toast('Usuario eliminado');
    loadUsers();
    loadDashboard();
  } catch {
    toast('Error de conexión', true);
  }
}

function showModalError(msg) {
  const el = document.getElementById('admin-modal-error');
  el.textContent = msg;
  el.style.display = 'block';
}
