# ChooseWise Final Demo — AI Recommendation Edition

ChooseWise is a decision-support web app for students and everyday users who feel stuck choosing between options like apartments, classes, jobs, or purchases.

This version is designed for your **final demo**:
- clear user + problem framing
- real working product
- visible cumulative progress
- actual AI recommendation flow
- safe API key handling for a public GitHub repo

## What changed in this version
1. **AI recommendation engine**
   - Uses the OpenAI API from the Flask backend
   - Generates a recommendation, rationale, risks, and next-step advice

2. **Secure key handling**
   - API key is read from environment variables only
   - No keys in source code
   - `.gitignore` prevents `.env` leaks
   - App can still run in fallback mode with no API key

3. **Improved walkthrough value**
   - Weighted scoring + AI reasoning together
   - Better final-demo story: structure + explanation + iteration

4. **Deployment-ready**
   - Includes `requirements.txt`, `gunicorn`, and Render config
   - Easy to publish as a live demo URL

---

## Local setup

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your local env file
Copy `.env.example` to `.env` and paste your real key:
```bash
cp .env.example .env
```

Then edit `.env`:
```env
OPENAI_API_KEY=your_real_key_here
CHOOSEWISE_MODEL=gpt-4.1-mini
FLASK_ENV=development
```

### 4. Run locally
```bash
python app.py
```

Open:
```text
http://127.0.0.1:5000
```

---

## Security notes
- **Never** commit `.env`
- **Never** put your key in frontend JavaScript or HTML
- **Never** call OpenAI directly from the browser
- Use a **server-side backend route** instead
- If you think a key leaked, rotate it immediately in the OpenAI dashboard

This repo is set up so you can safely publish it **as long as you do not commit your real `.env` file**.

---

## Deployment recommendation

### Best option: Render
Render is the easiest fit for this Flask app:
- connect GitHub repo
- set environment variable `OPENAI_API_KEY`
- build command:
```bash
pip install -r requirements.txt
```
- start command:
```bash
gunicorn app:app
```

### Render environment variables
Add in Render dashboard:
- `OPENAI_API_KEY`
- `CHOOSEWISE_MODEL=gpt-4.1-mini`

Optional:
- `PYTHON_VERSION=3.11.9`

---

## Final demo structure suggestion

### Value Proposition Opening
ChooseWise is for students and everyday users who struggle with decisions that involve tradeoffs. The problem is that people often compare options in a messy or emotional way, which makes it harder to feel confident. ChooseWise matters because it combines structured weighted scoring with AI-generated reasoning, so users can get both a numeric comparison and a plain-language recommendation.

### Live Walkthrough
- enter two options
- add criteria and weights
- rate each option
- click **Analyze**
- show weighted result
- show AI recommendation
- explain what success looks like: faster, clearer decisions with reasoning

### Cumulative Progress
1. Added weighted scoring
2. Added AI recommendation engine
3. Improved UX and explanation layout
4. Added deployment/security-ready architecture

### Reflection
- What worked: structure + explanation together
- What didn’t: only two options in this MVP
- Next step: more options, saved histories, collaborative decisions

---

## Files
- `app.py` Flask backend
- `templates/index.html` main UI
- `static/styles.css` styling
- `.env.example` example env vars
- `.gitignore` protects secrets
- `requirements.txt` dependencies
- `render.yaml` optional Render blueprint
- `canvas_submission_final.txt` ready-to-edit Canvas draft
- `demo_script_final.txt` ready-to-use final video script