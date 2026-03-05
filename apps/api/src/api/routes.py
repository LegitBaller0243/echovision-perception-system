import base64
import logging
import os
import sys
import tempfile
from time import perf_counter
from pathlib import Path

from flask import Blueprint, jsonify, request, Response, send_from_directory
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FRONTEND_DIST = PROJECT_ROOT / "apps" / "frontend" / "dist"

from integrations.audio.text_to_speech import text_to_speech as tts
from services.app_core.observability import ensure_trace_id, get_logger, log_event, stage_timer
from services.app_core.use_cases.orchestrator import process_auto_detect, process_query


routes = Blueprint('routes', __name__)
CORS(routes)
logger = get_logger(__name__)


@routes.route('/', methods=['GET'])
def home():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")

    return jsonify({
        "name": "KLR.ai API",
        "status": "running",
        "endpoints": ["/health", "/auto-detect", "/query", "/text-to-speech"],
        "hint": "Build frontend with `cd apps/frontend && npm run build` to serve UI at /",
    }), 200


@routes.route('/assets/<path:filename>', methods=['GET'])
def frontend_assets(filename):
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        return send_from_directory(assets_dir, filename)
    return Response(status=404)


@routes.route('/favicon.ico', methods=['GET'])
@routes.route('/apple-touch-icon.png', methods=['GET'])
@routes.route('/apple-touch-icon-precomposed.png', methods=['GET'])
def icon_placeholders():
    icon_name = Path(request.path).name
    icon_path = FRONTEND_DIST / icon_name
    if icon_path.exists():
        return send_from_directory(FRONTEND_DIST, icon_name)
    return Response(status=204)


@routes.route('/<path:path>', methods=['GET'])
def frontend_catch_all(path):
    candidate = FRONTEND_DIST / path
    if candidate.exists() and candidate.is_file():
        return send_from_directory(FRONTEND_DIST, path)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIST, "index.html")

    return jsonify({"error": f"Route '{path}' not found"}), 404


def decode_base64_image(base64_string: str) -> str:
    # Decode base64 string
    image_data = base64.b64decode(base64_string)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        tmp_file.write(image_data)
        tmp_path = tmp_file.name

    return tmp_path


@routes.route('/query', methods=['POST'])
def handle_query():
    trace_id = ensure_trace_id(request.headers.get("X-Trace-Id"))
    request_timings_ms = {}
    request_start = perf_counter()

    data = request.get_json()
    text_query = data.get('query')
    if not text_query or not isinstance(text_query, str):
        return jsonify({"error": "Query must be a non-empty string"}), 400

    base64_image = data.get('image')
    if not base64_image or not isinstance(base64_image, str):
        return jsonify({"error": "Image must be a base64-encoded string"}), 400

    image_path = None
    try:
        with stage_timer(request_timings_ms, "decode_image_ms"):
            image_path = decode_base64_image(base64_image)
        with stage_timer(request_timings_ms, "pipeline_ms"):
            result = process_query(text_query, image_path, trace_id=trace_id)
    finally:
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)

    request_timings_ms["total_request_ms"] = round((perf_counter() - request_start) * 1000, 2)
    log_event(
        logger,
        "api_request_complete",
        trace_id=trace_id,
        timings_ms=request_timings_ms,
    )
    return jsonify({
        "result": result,
        "trace_id": trace_id,
        "request_timings_ms": request_timings_ms,
    }), 200


@routes.route('/auto-detect', methods=['POST'])
def handle_auto_detect():
    trace_id = ensure_trace_id(request.headers.get("X-Trace-Id"))
    request_timings_ms = {}
    request_start = perf_counter()

    data = request.get_json()
    base64_image = data.get('image')
    if not base64_image or not isinstance(base64_image, str):
        return jsonify({"error": "Image must be a base64-encoded string"}), 400

    image_path = None
    try:
        with stage_timer(request_timings_ms, "decode_image_ms"):
            image_path = decode_base64_image(base64_image)
        with stage_timer(request_timings_ms, "pipeline_ms"):
            result = process_auto_detect(image_path, trace_id=trace_id)
    finally:
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)

    request_timings_ms["total_request_ms"] = round((perf_counter() - request_start) * 1000, 2)
    log_event(
        logger,
        "api_request_complete",
        trace_id=trace_id,
        timings_ms=request_timings_ms,
    )
    return jsonify({
        "result": result["response_text"],
        "trace_id": trace_id,
        "request_timings_ms": request_timings_ms,
        "pipeline_timings_ms": result.get("timings_ms", {}),
    }), 200


@routes.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@routes.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    trace_id = ensure_trace_id(request.headers.get("X-Trace-Id"))
    request_timings_ms = {}
    request_start = perf_counter()

    data = request.get_json()
    text = data.get('text', '')
    try:
        with stage_timer(request_timings_ms, "tts_endpoint_ms"):
            result = tts(text, trace_id=trace_id)
        request_timings_ms["total_request_ms"] = round((perf_counter() - request_start) * 1000, 2)
        log_event(
            logger,
            "api_request_complete",
            trace_id=trace_id,
            timings_ms=request_timings_ms,
        )
        return jsonify({
            **result,
            "trace_id": trace_id,
            "request_timings_ms": request_timings_ms,
        }), 200
    except Exception as e:
        log_event(
            logger,
            "api_request_failed",
            level=logging.ERROR,
            trace_id=trace_id,
            timings_ms=request_timings_ms,
        )
        return jsonify({"ok": False, "error": str(e), "trace_id": trace_id}), 502
