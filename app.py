# app.py
from flask import Flask, request, jsonify
from pest_akinator import PestAkinator, load_db
import uuid

app = Flask(__name__)
sessions = {}  # Guarda las sesiones activas del Akinator

@app.route('/')
def home():
    return jsonify({"status": "PestAkinator API online 🚀"})

@app.route('/start', methods=['POST'])
def start():
    """Inicia una nueva sesión de identificación"""
    db = load_db()
    session_id = str(uuid.uuid4())
    akin = PestAkinator(db)
    sessions[session_id] = akin

    q = akin.choose_best_question()
    return jsonify({
        "session_id": session_id,
        "question": akin.questions[q],
        "attribute": q
    })

@app.route('/answer', methods=['POST'])
def answer():
    """Recibe la respuesta del usuario (yes/no/unknown)"""
    data = request.get_json()
    session_id = data.get("session_id")
    attribute = data.get("attribute")
    answer = data.get("answer")

    if session_id not in sessions:
        return jsonify({"error": "Sesión no encontrada"}), 404

    akin = sessions[session_id]
    akin.update_with_answer(attribute, answer)

    # Verificar si ya hay alta probabilidad de identificación
    top = akin.top_candidates(1)[0]
    pest_id, prob = top

    if prob > 0.85 or len(akin.asked) >= 12:
        pest = next(p for p in akin.db["pests"] if p["id"] == pest_id)
        return jsonify({
            "finished": True,
            "pest": {
                "id": pest["id"],
                "name": pest["name"],
                "notes": pest["notes"]
            }
        })

    # Si no terminó, devolver siguiente pregunta
    next_q = akin.choose_best_question()
    if not next_q:
        candidates = [
            {"id": pid, "prob": pr}
            for pid, pr in akin.top_candidates(3)
        ]
        return jsonify({
            "finished": True,
            "candidates": candidates
        })

    return jsonify({
        "finished": False,
        "question": akin.questions[next_q],
        "attribute": next_q
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
