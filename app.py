# app.py
import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from pest_akinator import PestAkinator

app = Flask(__name__)
CORS(app)

# Knowledge engine (loads pests.json & questions.json)
engine = PestAkinator()

# session_id -> Session instance
sessions = {}

# optional: require a teach secret to protect POST /api/teach
TEACH_SECRET = os.environ.get("TEACH_SECRET")


@app.route("/")
def home():
    return "PestAkinator API - OK"


@app.route("/api/new_session", methods=["POST"])
def new_session():
    # create new session object
    session_id = str(uuid.uuid4())
    sessions[session_id] = engine.create_session()
    # choose first question
    attrs = engine.get_all_attributes()
    next_attr = sessions[session_id].choose_best_attribute(attrs)
    q_info = engine.get_question_info(next_attr) if next_attr else None
    return jsonify({"session_id": session_id, "next_question": q_info}), 201


@app.route("/api/question", methods=["GET"])
def get_question():
    session_id = request.args.get("session_id")
    if not session_id or session_id not in sessions:
        return jsonify({"error": "session not found"}), 404
    session = sessions[session_id]
    attrs = engine.get_all_attributes()
    next_attr = session.choose_best_attribute(attrs)
    if next_attr:
        q_info = engine.get_question_info(next_attr)
        return jsonify({"next_question": q_info})
    else:
        return jsonify({"next_question": None})


@app.route("/api/answer", methods=["POST"])
def answer():
    data = request.get_json() or {}
    session_id = data.get("session_id")
    attribute = data.get("attribute")
    answer = data.get("answer")  # 'yes' | 'no' | 'unknown'
    if not session_id or session_id not in sessions:
        return jsonify({"error": "session not found"}), 404
    if attribute is None or answer is None:
        return jsonify({"error": "attribute and answer required"}), 400

    session = sessions[session_id]
    session.update(attribute, answer)

    # choose next question
    attrs = engine.get_all_attributes()
    next_attr = session.choose_best_attribute(attrs)
    next_q = engine.get_question_info(next_attr) if next_attr else None

    # build full candidate info
    top = session.top_candidates(5)
    candidates = []
    for pid, prob in top:
        pest = engine.pests.get(pid, {})
        candidates.append({
            "id": pid,
            "name": pest.get("name"),
            "probability": round(prob, 3),
            "image": pest.get("image"),
            "notes": pest.get("notes", "")
        })

    return jsonify({"next_question": next_q, "candidates": candidates})


@app.route("/api/candidates", methods=["GET"])
def candidates():
    session_id = request.args.get("session_id")
    if not session_id or session_id not in sessions:
        return jsonify({"error": "session not found"}), 404
    session = sessions[session_id]
    top = session.top_candidates(10)
    candidates = []
    for pid, prob in top:
        pest = engine.pests.get(pid, {})
        candidates.append({
            "id": pid,
            "name": pest.get("name"),
            "probability": round(prob, 3),
            "image": pest.get("image"),
            "notes": pest.get("notes", "")
        })
    return jsonify({"candidates": candidates})


@app.route("/api/teach", methods=["POST"])
def teach():
    # optional security: require header 'X-TEACH-SECRET' if TEACH_SECRET set
    if TEACH_SECRET:
        secret = request.headers.get("X-TEACH-SECRET")
        if secret != TEACH_SECRET:
            return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    # expect full pest dict: id(optional), name, attributes (dict), image(optional), notes(optional), common_names(optional)
    if "name" not in data or "attributes" not in data:
        return jsonify({"error": "name and attributes required"}), 400
    pid = engine.add_new_pest(data)
    return jsonify({"status": "ok", "id": pid}), 201


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
