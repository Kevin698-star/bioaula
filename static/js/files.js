/**
 * BioAula · files.js
 * Manejo de carga y previsualización de archivos del material de clase con parsing real.
 */

import { state } from './state.js';
import { toast } from './ui.js';

const FILE_ICONS = {
  pdf: '📄', docx: '📝', doc: '📝', txt: '📋',
  png: '🖼', jpg: '🖼', jpeg: '🖼', md: '📝', csv: '📊', default: '📎',
};

// ── Drag & Drop ───────────────────────────────────────────────────────────────

export function onDragOver(e) {
  e.preventDefault();
  document.getElementById('upload-zone')?.classList.add('drag');
}

export function onDragLeave() {
  document.getElementById('upload-zone')?.classList.remove('drag');
}

export function onDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone')?.classList.remove('drag');
  handleFiles(e.dataTransfer.files);
}

// ── Procesamiento de archivos ─────────────────────────────────────────────────

/**
 * Procesa un FileList y los agrega al estado.
 * Imágenes → base64 para Gemini (inlineData).
 * PDF → base64 para Gemini multimodal + extracción de texto si es posible.
 * DOCX/TXT/CSV/MD → texto extraído.
 * @param {FileList} files
 */
export async function handleFiles(files) {
  for (const file of files) {
    const ext = file.name.split('.').pop().toLowerCase();
    const isImg = ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext);

    let content = '', type = 'text', mime = file.type;

    if (isImg) {
      content = await fileToBase64(file);
      type = 'image';
      mime = file.type || 'image/jpeg';
    } else if (ext === 'pdf') {
      const b64 = await fileToBase64(file);
      mime = 'application/pdf';
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/parse-file', { method: 'POST', body: formData });
        if (res.ok) {
          const parsed = await res.json();
          if (parsed.type === 'text' && parsed.content) {
            content = parsed.content;
            type = 'text';
          } else {
            // Passthrough: Gemini procesa PDFs nativamente mediante base64
            content = b64;
            type = 'pdf';
          }
        } else {
          content = b64;
          type = 'pdf';
        }
      } catch {
        content = b64;
        type = 'pdf';
      }
    } else {
      // DOCX, TXT, CSV, MD
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch('/api/parse-file', { method: 'POST', body: formData });
        if (res.ok) {
          const parsed = await res.json();
          if (parsed.type === 'text' && parsed.content) {
            content = parsed.content;
            type = 'text';
          } else if (ext === 'txt' || ext === 'csv' || ext === 'md') {
            content = await file.text();
            type = 'text';
          }
        } else if (ext === 'txt' || ext === 'csv' || ext === 'md') {
          content = await file.text();
          type = 'text';
        }
      } catch (err) {
        if (ext === 'txt' || ext === 'csv' || ext === 'md') {
          try { content = await file.text(); } catch (_) { content = ''; }
        }
        type = 'text';
      }
    }

    // Evitar duplicados del mismo nombre
    state.uploadedFiles = state.uploadedFiles.filter(f => f.name !== file.name);
    state.uploadedFiles.push({ name: file.name, content, type, mime });
  }

  renderFileList();
  toast(`${files.length} archivo(s) procesado(s)`);
}

function fileToBase64(file) {
  return new Promise(res => {
    const reader = new FileReader();
    reader.onload = () => res(reader.result.split(',')[1]);
    reader.readAsDataURL(file);
  });
}

// ── Render de la lista de archivos ────────────────────────────────────────────

export function renderFileList() {
  const container = document.getElementById('file-list');
  if (!container) return;

  container.innerHTML = state.uploadedFiles.map((f, i) => {
    const ext  = f.name.split('.').pop().toLowerCase();
    const icon = FILE_ICONS[ext] || FILE_ICONS.default;
    return `
      <div class="file-chip">
        <span>${icon}</span>
        <span class="file-chip-name">${f.name}</span>
        <span class="file-chip-remove" data-index="${i}">✕</span>
      </div>`;
  }).join('');

  container.querySelectorAll('.file-chip-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      state.uploadedFiles.splice(Number(btn.dataset.index), 1);
      renderFileList();
    });
  });
}

// ── Construir partes de Gemini desde archivos ─────────────────────────────────

/**
 * Convierte los archivos cargados en partes listas para enviar a Gemini.
 * Imágenes y PDFs binarios → inlineData con mimeType.
 * Textos → text con preview.
 * @returns {Array} extraParts para callGemini()
 */
export function buildGeminiFileParts() {
  return state.uploadedFiles.map(f => {
    if (f.type === 'image') {
      return { inlineData: { mimeType: f.mime || 'image/jpeg', data: f.content } };
    }
    if (f.type === 'pdf') {
      return { inlineData: { mimeType: 'application/pdf', data: f.content } };
    }
    return { text: `[Contenido del archivo "${f.name}"]:\n${f.content.substring(0, 25000)}` };
  });
}
