from flask import request, jsonify
from . import rag_bp


@rag_bp.route('/index-document', methods=['POST'])
def index_document():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Cuerpo de la petición inválido'}), 400

    document_id = data.get('document_id')
    text = data.get('text', '')

    if not document_id or not str(document_id).strip():
        return jsonify({'error': 'document_id es requerido'}), 400
    if not text or not str(text).strip():
        return jsonify({'error': 'text es requerido'}), 400

    # Límite preventivo de seguridad: 2 MB de texto
    if len(text) > 2_000_000:
        text = text[:2_000_000]

    try:
        from .retrieval import index_document as _index
        chunks = _index(str(document_id).strip(), text)
        return jsonify({'chunks_indexados': chunks, 'document_id': document_id})
    except Exception as e:
        return jsonify({'error': f'Error al indexar: {str(e)}'}), 500


@rag_bp.route('/search', methods=['POST'])
def search():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Cuerpo de la petición inválido'}), 400

    query = data.get('query', '')
    document_id = data.get('document_id')

    if not query or not str(query).strip():
        return jsonify({'error': 'query es requerido'}), 400

    try:
        from .retrieval import search_document
        context = search_document(str(query).strip(), n_results=10, document_id=document_id)
        return jsonify({'context': context})
    except Exception as e:
        return jsonify({'error': f'Error al buscar: {str(e)}'}), 500
