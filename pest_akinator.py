# pest_akinator.py
import json
import math
import os
import re
import uuid

def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or str(uuid.uuid4())[:8]

class Session:
    """Estado por sesión: probabilidades y atributos preguntados."""
    def __init__(self, pests):
        self.pests = pests  # dict: pest_id -> pest_dict
        n = len(pests)
        if n > 0:
            self.current_probs = {pid: 1.0 / n for pid in pests}
        else:
            self.current_probs = {}
        self.asked_attributes = set()

    def normalize(self):
        total = sum(self.current_probs.values())
        if total <= 0:
            n = len(self.current_probs) or 1
            self.current_probs = {k: 1.0 / n for k in self.current_probs}
        else:
            for k in self.current_probs:
                self.current_probs[k] /= total

    def update(self, attribute, answer):
        """
        answer: 'yes' | 'no' | 'unknown'
        Uses simple Bayes-like update:
        P(answer|pest) = attr_prob if yes, (1-attr_prob) if no, 1.0 if unknown
        """
        if not self.current_probs:
            return
        for pid in list(self.current_probs.keys()):
            pest = self.pests[pid]
            attr_prob = float(pest.get("attributes", {}).get(attribute, 0.5))
            if answer == "yes":
                likelihood = attr_prob
            elif answer == "no":
                likelihood = 1.0 - attr_prob
            else:  # unknown
                likelihood = 1.0
            self.current_probs[pid] *= max(likelihood, 1e-9)
        self.normalize()
        self.asked_attributes.add(attribute)

    def entropy(self, probs_dict):
        ps = [p for p in probs_dict if p > 0]
        if not ps:
            return 0.0
        return -sum(p * math.log(p, 2) for p in ps)

    def expected_entropy_after(self, attribute):
        """
        Compute expected entropy after asking attribute.
        """
        # Probability of "yes" and "no"
        P_yes = 0.0
        yes_post = {}
        no_post = {}
        for pid, prob in self.current_probs.items():
            attr_prob = float(self.pests[pid].get("attributes", {}).get(attribute, 0.5))
            P_yes += prob * attr_prob
            yes_post[pid] = prob * attr_prob
            no_post[pid] = prob * (1 - attr_prob)
        P_no = sum(no_post.values())

        # normalize posteriors and compute entropy
        e_yes = 0.0
        e_no = 0.0
        if P_yes > 0:
            e_yes = self.entropy([v / P_yes for v in yes_post.values() if v > 0])
        if P_no > 0:
            e_no = self.entropy([v / P_no for v in no_post.values() if v > 0])

        expected = P_yes * e_yes + P_no * e_no
        current_H = self.entropy(list(self.current_probs.values()))
        # information gain:
        gain = current_H - expected
        return gain

    def choose_best_attribute(self, attributes_list):
        remaining = [a for a in attributes_list if a not in self.asked_attributes]
        if not remaining:
            return None
        best_attr = None
        best_gain = -1.0
        for a in remaining:
            gain = self.expected_entropy_after(a)
            if gain > best_gain:
                best_gain = gain
                best_attr = a
        return best_attr

    def top_candidates(self, n=5):
        items = sorted(self.current_probs.items(), key=lambda x: x[1], reverse=True)[:n]
        return items

class PestAkinator:
    def __init__(self, pests_path="pests.json", questions_path="questions.json"):
        self.pests_path = pests_path
        self.questions_path = questions_path
        self.reload()

    def reload(self):
        raw_pests = _load_json(self.pests_path)
        # support two formats: dict keyed by id or list
        if isinstance(raw_pests, list):
            self.pests = {p["id"]: p for p in raw_pests}
        elif isinstance(raw_pests, dict):
            # assume already keyed by id
            self.pests = raw_pests
        else:
            self.pests = {}
        self.questions = _load_json(self.questions_path) or {}

    def create_session(self):
        self.reload()  # ensure fresh knowledge
        return Session(self.pests)

    def get_all_attributes(self):
        attrs = set()
        for p in self.pests.values():
            attrs.update(p.get("attributes", {}).keys())
        return sorted(list(attrs))

    def get_question_info(self, attribute):
        q = self.questions.get(attribute, {})
        return {
            "attribute": attribute,
            "question": q.get("question", f"¿El atributo '{attribute}' está presente?"),
            "image": q.get("image")
        }

    def add_new_pest(self, pest_data):
        # Ensure id
        if "id" not in pest_data or not pest_data["id"]:
            pest_data["id"] = _slugify(pest_data.get("name", "pest"))
        # Avoid collide
        pid = pest_data["id"]
        if pid in self.pests:
            pid = f"{pid}_{str(uuid.uuid4())[:6]}"
            pest_data["id"] = pid
        self.pests[pid] = pest_data
        _save_json(self.pests_path, self.pests)
        return pid
