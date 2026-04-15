import os
from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = Flask(__name__)

MODEL = os.getenv("CHOOSEWISE_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

def calculate_weighted_totals(criteria, weights, option_a_scores, option_b_scores):
    rows = []
    total_a = 0
    total_b = 0

    for i, criterion in enumerate(criteria):
        c = criterion.strip() or f"Criterion {i+1}"
        w = safe_int(weights[i])
        a = safe_int(option_a_scores[i])
        b = safe_int(option_b_scores[i])

        weighted_a = w * a
        weighted_b = w * b
        total_a += weighted_a
        total_b += weighted_b

        rows.append({
            "criterion": c,
            "weight": w,
            "option_a_score": a,
            "option_b_score": b,
            "option_a_weighted": weighted_a,
            "option_b_weighted": weighted_b,
        })

    return rows, total_a, total_b

def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def build_decision_payload(option_a_name, option_b_name, rows, total_a, total_b):
    return {
        "option_a": option_a_name,
        "option_b": option_b_name,
        "weighted_total_a": total_a,
        "weighted_total_b": total_b,
        "criteria": rows,
    }

def fallback_recommendation(payload):
    option_a = payload["option_a"]
    option_b = payload["option_b"]
    total_a = payload["weighted_total_a"]
    total_b = payload["weighted_total_b"]

    if total_a > total_b:
        winner = option_a
        loser = option_b
    elif total_b > total_a:
        winner = option_b
        loser = option_a
    else:
        winner = "Tie"
        loser = None

    if winner == "Tie":
        recommendation = (
            "These two options came out evenly in the weighted scoring. "
            "A good next step would be to add one more decision criterion or increase "
            "the weights on the factors you care about most."
        )
    else:
        recommendation = (
            f"Based on the weighted scores, {winner} is the stronger option right now. "
            f"It performs better on the factors you marked as most important."
        )

    return {
        "mode": "fallback",
        "summary": recommendation,
        "best_option": winner,
        "key_reasoning": [
            "This fallback mode uses weighted scoring only.",
            f"{option_a} total: {total_a}",
            f"{option_b} total: {total_b}",
        ],
        "risks": [
            "Numeric scores may not capture every real-world factor.",
            "You may want to add cost, time, or personal fit if those matter."
        ],
        "next_step": (
            f"Review the top-weighted criteria and double-check whether the lower-scoring option, "
            f"{loser if loser else 'either option'}, has any hidden advantages."
        )
    }

def ai_recommendation(payload):
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback_recommendation(payload)

    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
You are helping a user choose between two options.

Return a concise recommendation in JSON with these exact keys:
summary, best_option, key_reasoning, risks, next_step

Rules:
- best_option must be either "{payload["option_a"]}", "{payload["option_b"]}", or "Tie"
- key_reasoning must be a JSON array of 2 to 4 short bullet-style strings
- risks must be a JSON array of 1 to 3 short bullet-style strings
- Keep the answer grounded in the structured data below
- Do not invent external facts
- If scores are close, acknowledge uncertainty

Structured decision data:
{payload}
""".strip()

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    text = getattr(response, "output_text", "").strip()
    if not text:
        return fallback_recommendation(payload)

    import json
    try:
        parsed = json.loads(text)
        parsed["mode"] = "openai"
        return parsed
    except Exception:
        return {
            "mode": "openai",
            "summary": text,
            "best_option": "See summary",
            "key_reasoning": ["The model returned a plain-text recommendation."],
            "risks": ["Review the recommendation for completeness."],
            "next_step": "Use the structured scoring table to validate the recommendation."
        }

@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "rows": None,
        "total_a": None,
        "total_b": None,
        "recommendation": None,
        "used_ai": False,
    }

    if request.method == "POST":
        option_a_name = request.form.get("option_a_name", "Option A").strip() or "Option A"
        option_b_name = request.form.get("option_b_name", "Option B").strip() or "Option B"

        criteria = request.form.getlist("criteria")
        weights = request.form.getlist("weights")
        option_a_scores = request.form.getlist("option_a_scores")
        option_b_scores = request.form.getlist("option_b_scores")

        rows, total_a, total_b = calculate_weighted_totals(
            criteria, weights, option_a_scores, option_b_scores
        )

        payload = build_decision_payload(option_a_name, option_b_name, rows, total_a, total_b)
        recommendation = ai_recommendation(payload)

        context.update({
            "option_a_name": option_a_name,
            "option_b_name": option_b_name,
            "rows": rows,
            "total_a": total_a,
            "total_b": total_b,
            "recommendation": recommendation,
            "used_ai": recommendation.get("mode") == "openai",
        })

    return render_template("index.html", **context)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)