# pest_akinator.py
import json, math, os
from copy import deepcopy

DB_FILE = 'pest_db.json'

# ---------- Dataset inicial ----------
INITIAL_DB = {
    "pests": [
        {
            "id": "spodoptera_frugiperda",
            "name": "Gusano cogollero (Spodoptera frugiperda)",
            "notes": "Principal plaga del maíz; las larvas se alimentan de hojas y cogollos causando daños severos.",
            "img":"",
            "attributes": {
                "host_maize": 0.95,
                "chews_leaves": 0.95,
                "frass_present": 0.9,
                "nocturnal": 0.8,
                "larva_visible_on_whorl": 0.9,
                "causes_dead_hearts": 0.7
            }
        },
        {
            "id": "ostrinia_nubilalis",
            "name": "Barrenador del maíz (Ostrinia nubilalis)",
            "notes": "Larva que perfora tallos y mazorcas del maíz, provocando marchitez.",
            "img":"",
            "attributes": {
                "host_maize": 0.9,
                "chews_leaves": 0.4,
                "frass_present": 0.6,
                "larva_inside_stem": 0.9,
                "holes_in_stem": 0.8,
                "causes_dead_hearts": 0.6
            }
        },
        {
            "id": "tuta_absoluta",
            "name": "Minador de la hoja del tomate (Tuta absoluta)",
            "notes": "Ataca tomate; causa galerías en hojas y frutos.",
            "img":"",
            "attributes": {
                "host_tomato": 0.95,
                "leaf_mines": 0.95,
                "small_holes_in_leaves": 0.9,
                "high_reproduction": 0.9,
                "larva_small_and_green": 0.7
            }
        },
        {
            "id": "bemisia_tabaci",
            "name": "Mosca blanca (Bemisia tabaci)",
            "notes": "Insecto chupador que causa amarillamiento y secreción de melaza en hojas.",
            "img":"",
            "attributes": {
                "sucking_insect": 0.95,
                "white_tiny_insects_on_underside": 0.95,
                "honeydew_exudate": 0.9,
                "transmits_viruses": 0.7
            }
        },
        {
            "id": "helicoverpa_armigera",
            "name": "Helicoverpa (gusano del algodón/tomate)",
            "notes": "Oruga que se alimenta de flores, frutos y hojas de múltiples cultivos.",
            "img":"",
            "attributes": {
                "chews_flowers_and_fruits": 0.9,
                "polyphagous": 0.85,
                "visible_caterpillar": 0.9,
                "frass_present": 0.7
            }
        }
    ],
    "questions": {
        "host_maize": "¿El cultivo afectado es maíz?",
        "chews_leaves": "¿Ves hojas con bordes irregulares o agujeros grandes?",
        "frass_present": "¿Hay excremento (frass) visible cerca de las hojas o cogollos?",
        "nocturnal": "¿El daño parece más activo durante la noche?",
        "larva_visible_on_whorl": "¿Ves orugas dentro del cogollo de la planta?",
        "causes_dead_hearts": "¿Las plantas tienen el tallo central seco ('dead heart')?",
        "larva_inside_stem": "¿Hay larvas dentro del tallo?",
        "holes_in_stem": "¿Se observan agujeros en el tallo?",
        "host_tomato": "¿El cultivo afectado es tomate?",
        "leaf_mines": "¿Hay galerías o minas visibles en las hojas?",
        "small_holes_in_leaves": "¿Ves hoyos pequeños en las hojas?",
        "high_reproduction": "¿Hay muchos individuos (alta reproducción)?",
        "larva_small_and_green": "¿Las larvas son pequeñas y de color verde?",
        "sucking_insect": "¿El insecto parece succionar (hojas amarillas o pegajosas)?",
        "white_tiny_insects_on_underside": "¿Hay insectos blancos pequeños en el envés de las hojas?",
        "honeydew_exudate": "¿Notas melaza o residuos pegajosos?",
        "transmits_viruses": "¿Las plantas muestran síntomas de virus (moteado, deformación)?",
        "chews_flowers_and_fruits": "¿Se comen flores o frutos?",
        "polyphagous": "¿Ataca varios tipos de cultivos?",
        "visible_caterpillar": "¿Ves orugas grandes y visibles?"
    }
}

# ---------- Utilidades ----------
def entropy(probs):
    e = 0.0
    for p in probs:
        if p > 0:
            e -= p * math.log2(p)
    return e

def normalize(d):
    total = sum(d.values())
    if total == 0:
        return {k: 1.0 / len(d) for k in d}
    return {k: v / total for k, v in d.items()}

def load_db(file=DB_FILE):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_db(INITIAL_DB, file)
        return deepcopy(INITIAL_DB)

def save_db(db, file=DB_FILE):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ---------- Motor principal ----------
class PestAkinator:
    def __init__(self, db):
        self.db = db
        self.questions = db["questions"]
        self.probs = normalize({p["id"]: 1.0 for p in db["pests"]})
        self.asked = set()

    def get_attribute_prob(self, pest_id, attribute):
        pest = next((p for p in self.db["pests"] if p["id"] == pest_id), None)
        return pest["attributes"].get(attribute, 0.5) if pest else 0.5

    def expected_entropy_after_question(self, attribute):
        P_yes = sum(self.probs[p] * self.get_attribute_prob(p, attribute) for p in self.probs)
        P_no = 1 - P_yes
        post_yes = normalize({p: self.probs[p] * self.get_attribute_prob(p, attribute) for p in self.probs})
        post_no = normalize({p: self.probs[p] * (1 - self.get_attribute_prob(p, attribute)) for p in self.probs})
        e_yes = entropy(post_yes.values())
        e_no = entropy(post_no.values())
        return P_yes * e_yes + P_no * e_no

    def choose_best_question(self):
        best_q, best_score = None, float("inf")
        for attr in self.questions:
            if attr in self.asked:
                continue
            e = self.expected_entropy_after_question(attr)
            if e < best_score:
                best_q, best_score = attr, e
        return best_q

    def update_with_answer(self, attribute, answer):
        for p in self.probs:
            a = self.get_attribute_prob(p, attribute)
            likelihood = a if answer == "yes" else (1 - a if answer == "no" else 1.0)
            self.probs[p] *= likelihood
        self.probs = normalize(self.probs)
        self.asked.add(attribute)

    def top_candidates(self, n=3):
        return sorted(self.probs.items(), key=lambda x: x[1], reverse=True)[:n]
