"""
BioAula — Servidor Flask
Lógica central de la plataforma educativa con IA.
"""

import sys
import os
import json
import urllib.request
import urllib.error

# Asegurar que el directorio de bioaula esté en el path de búsqueda de Python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

# Cargar variables de entorno inmediatamente
load_dotenv(os.path.join(BASE_DIR, '.env'))

from flask import render_template, request, jsonify
from backend import create_app

app = create_app()


# ─── Rutas de autenticación (páginas) ─────────────────────────────────────────

@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


# ─── Ruta pública para pruebas compartidas ────────────────────────────────────

@app.route("/quiz/<int:quiz_id>")
def shared_quiz(quiz_id):
    return render_template("index.html")


# ─── Rutas principales ───────────────────────────────────────────────────────

@app.route("/")
def index():
    """Página principal — detecta modo estudiante desde query params."""
    mode = request.args.get("mode", "")
    quiz_param = request.args.get("quiz", "") or request.args.get("data", "")
    return render_template("index.html", student_mode=(mode == "estudiante"), quiz_param=quiz_param)


# ─── API: Validación de API Key ───────────────────────────────────────────────

@app.route("/api/validate-key", methods=["POST"])
def validate_key():
    """Valida formato básico de la API Key de Gemini."""
    data = request.get_json(silent=True) or {}
    key = data.get("key", "").strip()
    if not key.startswith("AIza"):
        return jsonify({"valid": False, "error": "La API Key debe empezar con 'AIza...'"}), 400
    return jsonify({"valid": True})


# ─── API: Parsing real de archivos (TXT, CSV, MD, PDF, DOCX) ─────────────────

@app.route("/api/parse-file", methods=["POST"])
def parse_file():
    """
    Recibe un archivo del cliente, extrae su texto legible y lo devuelve.
    Soporta TXT, CSV, MD, DOCX (con descompresión nativa XML) y PDF.
    """
    if "file" not in request.files:
        return jsonify({"error": "No se recibió archivo"}), 400

    file = request.files["file"]
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    text_types = {"txt", "md", "csv"}

    if ext in text_types:
        try:
            file.stream.seek(0)
            raw = file.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            return jsonify({"type": "text", "content": content[:50000], "name": filename})
        except Exception as e:
            return jsonify({"error": f"Error al leer archivo de texto: {str(e)}"}), 500

    if ext == "pdf":
        try:
            file.stream.seek(0)
            raw = file.read()
            # Intentar extracción si el módulo pypdf está disponible
            try:
                import io
                pypdf_mod = __import__("pypdf")
                reader = pypdf_mod.PdfReader(io.BytesIO(raw))
                pages = [p.extract_text() for p in reader.pages[:40] if p.extract_text()]
                content = "\n\n".join(pages)
                if content.strip():
                    return jsonify({"type": "text", "content": content[:50000], "name": filename})
            except Exception:
                pass
        except Exception:
            pass
        return jsonify({"type": "passthrough", "name": filename})

    if ext in ("docx", "doc"):
        try:
            file.stream.seek(0)
            raw = file.read()
            # Extracción nativa estándar de texto desde word/document.xml (sin dependencias externas)
            import io
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                if 'word/document.xml' in zf.namelist():
                    xml_data = zf.read('word/document.xml')
                    tree = ET.fromstring(xml_data)
                    texts = [elem.text for elem in tree.iter() if elem.tag.endswith('}t') and elem.text]
                    content = " ".join(texts)
                    if content.strip():
                        return jsonify({"type": "text", "content": content[:50000], "name": filename})
        except Exception:
            pass
        return jsonify({"type": "passthrough", "name": filename})

    return jsonify({"type": "passthrough", "name": filename})


# ─── API: Generar prompts de Gemini ──────────────────────────────────────────

@app.route("/api/build-prompts", methods=["POST"])
def build_prompts():
    """
    Recibe los parámetros de la prueba y devuelve los prompts estructurados
    listos para el generador con instrucciones pedagógicas precisas.
    """
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()
    nivel = data.get("nivel", "bachillerato")
    bank_size = int(data.get("bankSize", 30))
    num_q = int(data.get("numQ", 10))
    mat_text = data.get("materialText", "").strip()
    urls = data.get("urls", "").strip()

    if not topic:
        return jsonify({"error": "El tema es requerido"}), 400

    material = f"Tema: {topic}\nNivel: {nivel}"
    if urls:
        material += f"\nURLs de referencia: {urls}"
    if mat_text:
        material += f"\n\nMaterial de estudio:\n{mat_text}"

    quiz_prompt = f"""Eres un generador de exámenes de alta calidad. Tu única tarea es producir JSON válido. No escribas nada fuera del JSON.

MATERIAL DE ESTUDIO:
{material}

INSTRUCCIÓN: Genera exactamente {bank_size} preguntas de selección múltiple para un banco de prueba de nivel {nivel}.

Reglas pedagógicas obligatorias:
- 4 opciones por pregunta (solo UNA correcta, índice 0-3)
- Cubre equilibradamente TODOS los subtemas del material
- Distribuye niveles cognitivos: memorización, comprensión, aplicación y análisis
- Distractores plausibles y educativos (no absurdos)
- Asigna a cada pregunta un "subtema" corto (máx 4 palabras)

FORMATO DE RESPUESTA — devuelve EXACTAMENTE esto, sin texto antes ni después, sin backticks:
{{"preguntas":[{{"pregunta":"texto de la pregunta","opciones":["opción A","opción B","opción C","opción D"],"correcta":0,"explicacion":"explicación concisa y educativa","subtema":"nombre subtema"}}]}}"""

    apoyo_prompt = f"""{material}

Genera una guía de estudio estructurada y motivadora para los estudiantes con:
1. Conceptos clave del tema (6 a 8 conceptos bien explicados)
2. Una analogía cotidiana para entender el concepto central
3. Mapa conceptual esquemático en texto
4. 3 datos curiosos o aplicaciones reales en el mundo
5. 3 preguntas reflexivas de autoevaluación

Escribe con tono empático para nivel {nivel}. Máximo 450 palabras."""

    return jsonify({
        "quizPrompt": quiz_prompt,
        "apoyoPrompt": apoyo_prompt,
        "quizSystem": "Eres un generador de JSON educativo. Responde ÚNICAMENTE con el objeto JSON solicitado, sin explicaciones ni markdown.",
        "apoyoSystem": "Eres un profesor de biología y ciencias naturales empático, claro y pedagógico. Responde en español.",
        "numQ": num_q,
        "bankSize": bank_size,
        "topic": topic,
        "nivel": nivel,
    })


# ─── API: Prompts de análisis pedagógico ─────────────────────────────────────

@app.route("/api/teacher-analysis-prompt", methods=["POST"])
def teacher_analysis_prompt():
    """Genera el prompt de análisis pedagógico para el profesor."""
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "")
    weak_topics = data.get("weakTopics", [])
    avg = data.get("avg", 0)
    num_students = data.get("numStudents", 0)

    debiles_text = "\n".join(
        f"- {s.get('sub', '')}: {s.get('pct', 0)}% de acierto" for s in weak_topics
    ) if weak_topics else "Sin áreas marcadamente débiles."

    prompt = f"""Soy el profesor de "{topic}". Estos son los subtemas donde el grupo tuvo menor desempeño (% de acierto):
{debiles_text}

Promedio general del grupo: {avg}%
Número de estudiantes: {num_students}

Genera recomendaciones pedagógicas concretas para el profesor:
1. Qué actividades o estrategias usar para reforzar cada subtema débil
2. Cómo reorganizar el tiempo de clase
3. Recursos o dinámicas específicas recomendadas
4. Si hay patrones de error que sugieran una mala comprensión de un concepto base

Máximo 300 palabras. Dirígete al profesor en tono profesional."""

    return jsonify({
        "prompt": prompt,
        "system": "Eres un experto en pedagogía de ciencias naturales. Responde en español.",
    })


# ─── API: Prompt y ejecución de retroalimentación para el estudiante ──────────

@app.route("/api/student-feedback-prompt", methods=["POST"])
def student_feedback_prompt():
    """Genera el prompt de retroalimentación personalizada para el estudiante."""
    data = request.get_json(silent=True) or {}
    student_name = data.get("studentName", "Estudiante")
    topic = data.get("topic", "")
    pct = int(data.get("pct", 0))
    weak_topics = data.get("weakTopics", [])
    wrong_items = data.get("wrongItems", [])

    wrong_text = "\n\n".join(
        f"Pregunta: {w.get('pregunta', '')}\nSubtema: {w.get('subtema', '')}\n"
        f"Respuesta elegida: {w.get('opcionElegida', '')}\nCorrecta: {w.get('opcionCorrecta', '')}"
        for w in wrong_items
    )

    if pct >= 80:
        prompt = (
            f"El estudiante {student_name} obtuvo {pct}% en \"{topic}\". ¡Lo hizo muy bien!\n\n"
            "Domina todos o casi todos los subtemas. Genera un mensaje de felicitación motivador "
            "(máx 80 palabras), y luego sugiere 2 formas de profundizar o aplicar el conocimiento "
            "en la vida real. Dirígete de \"tú\"."
        )
    else:
        prompt = (
            f"El estudiante {student_name} obtuvo {pct}% en \"{topic}\".\n\n"
            f"Falló en estos subtemas: {', '.join(weak_topics) if weak_topics else 'conceptos varios'}.\n\n"
            f"Errores específicos:\n{wrong_text}\n\n"
            "Genera un material de refuerzo personalizado: dirígete al estudiante de \"tú\", "
            "sé motivador, incluye una analogía para el concepto más fallido, un ejemplo práctico "
            "y 2 ejercicios breves de práctica. Máximo 250 palabras."
        )

    return jsonify({
        "prompt": prompt,
        "system": "Eres un profesor de biología empático. Responde en español.",
    })


@app.route("/api/execute-gemini", methods=["POST"])
def execute_gemini():
    """
    Proxy seguro para llamar a Gemini desde el backend.
    Permite que los estudiantes sin API Key local reciban retroalimentación
    usando la clave del servidor o la clave proporcionada por el docente.
    """
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    system = data.get("system", "")
    api_key = data.get("apiKey", "").strip() or app.config.get("GEMINI_API_KEY", "")

    if not api_key:
        return jsonify({"error": "No hay API Key configurada para procesar la solicitud"}), 400
    if not prompt:
        return jsonify({"error": "Prompt requerido"}), 400

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4096},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            text = resp_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return jsonify({"text": text})
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        return jsonify({"error": f"Error de Gemini: {e.code}", "details": err_msg}), 502
    except Exception as e:
        return jsonify({"error": f"Error de conexión con IA: {str(e)}"}), 500


# ─── Punto de entrada ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
