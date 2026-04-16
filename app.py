import os
import json
import re
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = Flask(__name__)

MODEL = os.getenv("CHOOSEWISE_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
app.secret_key = os.getenv("SECRET_KEY", "choosewise-dev-key")


def strip_markdown_fences(text):
    """Remove markdown code fences that OpenAI sometimes wraps around JSON."""
    text = text.strip()
    match = re.match(r'^```(?:json)?\s*\n?(.*?)\n?```$', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def safe_int(value, default=5):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def calculate_weighted_totals(criteria_names, weights, scores, option_names):
    """
    criteria_names: list[str]
    weights:        list[int]
    scores:         list[list[int]] — scores[i][j] = criterion i, option j
    option_names:   list[str]

    Returns rows (list of dicts), totals (list of int, one per option).
    """
    n_options = len(option_names)
    totals = [0] * n_options
    rows = []

    for i, criterion in enumerate(criteria_names):
        w = safe_int(weights[i]) if i < len(weights) else 5
        criterion_scores = scores[i] if i < len(scores) else []

        raw = []
        weighted = []
        for j in range(n_options):
            s = safe_int(criterion_scores[j]) if j < len(criterion_scores) else 5
            ws = w * s
            raw.append(s)
            weighted.append(ws)
            totals[j] += ws

        rows.append({
            "criterion": criterion.strip() or f"Criterion {i + 1}",
            "weight": w,
            "scores": raw,
            "weighted": weighted,
            "max_weighted": max(weighted) if weighted else 0,
            "min_weighted": min(weighted) if weighted else 0,
        })

    return rows, totals


def build_decision_payload(option_names, rows, totals):
    totals_dict = {option_names[j]: totals[j] for j in range(len(option_names))}
    return {
        "options": option_names,
        "totals": totals_dict,
        "criteria": rows,
    }


def find_top_criterion(rows):
    """Return the row with the largest spread between best and worst weighted scores."""
    if not rows:
        return None
    def spread(row):
        w = row["weighted"]
        return max(w) - min(w) if len(w) >= 2 else 0
    return max(rows, key=spread)


def fallback_recommendation(payload):
    options = payload["options"]
    totals = payload["totals"]

    ranked = sorted(options, key=lambda o: totals[o], reverse=True)
    winner = ranked[0]

    if len(ranked) > 1 and totals[ranked[0]] == totals[ranked[1]]:
        winner = "Tie"
        summary = (
            "The top options scored equally in the weighted scoring. "
            "Try adjusting weights or adding a tiebreaker criterion."
        )
    else:
        summary = (
            f"Based on the weighted scores, {winner} is the strongest choice. "
            f"It outperforms the other options across your highest-weighted criteria."
        )

    score_lines = [f"{i + 1}. {name}: {totals[name]} pts" for i, name in enumerate(ranked)]

    return {
        "mode": "fallback",
        "best_option": winner,
        "ranking": ranked,
        "summary": summary,
        "key_reasoning": ["Score-based ranking (no AI key configured)."] + score_lines,
        "risks": [
            "Numeric scores may not capture every real-world factor.",
            "Consider adding criteria for cost, time, or personal fit if relevant.",
        ],
        "next_step": (
            f"Review your highest-weighted criteria and verify whether "
            f"{ranked[-1] if len(ranked) > 1 else 'lower-scoring options'} "
            f"might have advantages not captured in the scores."
        ),
    }


def ai_recommendation(payload):
    if not OPENAI_API_KEY or OpenAI is None:
        return fallback_recommendation(payload)

    client = OpenAI(api_key=OPENAI_API_KEY)
    options_list = ", ".join(f'"{o}"' for o in payload["options"])

    prompt = f"""
You are helping a user choose between {len(payload["options"])} options.

Return a concise recommendation as JSON with these exact keys:
best_option, ranking, summary, key_reasoning, risks, next_step

Rules:
- best_option must be exactly one of: {options_list}
- ranking must be a JSON array of ALL option names ordered from best to worst
- key_reasoning must be a JSON array of 2 to 4 short bullet-style strings
- risks must be a JSON array of 1 to 3 short bullet-style strings
- Keep the answer grounded in the structured data below
- Do not invent external facts
- If scores are close, acknowledge the uncertainty

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

    clean = strip_markdown_fences(text)
    try:
        parsed = json.loads(clean)
        parsed["mode"] = "openai"
        # Ensure ranking exists; fall back to score-sorted order
        if "ranking" not in parsed or not isinstance(parsed["ranking"], list):
            totals = payload["totals"]
            parsed["ranking"] = sorted(payload["options"], key=lambda o: totals.get(o, 0), reverse=True)
        return parsed
    except Exception:
        return {
            "mode": "openai",
            "best_option": "See summary",
            "ranking": [],
            "summary": clean,
            "key_reasoning": ["The model returned a plain-text recommendation."],
            "risks": ["Review the recommendation for completeness."],
            "next_step": "Use the structured scoring table to validate the recommendation.",
        }


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "option_names": None,
        "rows": None,
        "totals": None,
        "ranked_options": None,
        "recommendation": None,
        "used_ai": False,
        "top_criterion": None,
    }

    if request.method == "POST":
        try:
            option_names = json.loads(request.form.get("option_names_json", "[]"))
            criteria_names = json.loads(request.form.get("criteria_json", "[]"))
            weights = json.loads(request.form.get("weights_json", "[]"))
            scores = json.loads(request.form.get("scores_json", "[]"))
        except (ValueError, KeyError):
            return render_template("index.html", **context, error="Invalid form data. Please try again.")

        if len(option_names) < 2 or len(criteria_names) < 1:
            return render_template("index.html", **context, error="Please enter at least 2 options and 1 criterion.")

        rows, totals = calculate_weighted_totals(criteria_names, weights, scores, option_names)
        payload = build_decision_payload(option_names, rows, totals)
        recommendation = ai_recommendation(payload)

        ranked_options = sorted(
            zip(option_names, totals),
            key=lambda x: x[1],
            reverse=True
        )

        # Store results in session, then redirect so a page refresh
        # hits GET with an empty session — results won't reappear.
        session["result"] = {
            "option_names": option_names,
            "rows": rows,
            "totals": totals,
            "ranked_options": [list(pair) for pair in ranked_options],
            "recommendation": recommendation,
            "used_ai": recommendation.get("mode") == "openai",
            "top_criterion": find_top_criterion(rows),
        }
        return redirect(url_for("index"))

    # GET: read results once from session, then clear them.
    result = session.pop("result", None)
    if result:
        context.update(result)

    return render_template("index.html", **context)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
