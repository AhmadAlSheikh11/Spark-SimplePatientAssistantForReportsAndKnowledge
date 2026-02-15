# server.py
# Run: python server.py
# Open:
#   http://127.0.0.1:5000/          (EN)
#   http://127.0.0.1:5000/ar        (AR)

import os
import json
import secrets
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    request,
    send_from_directory,
    jsonify,
    redirect,
    session,
)
from werkzeug.utils import secure_filename

# ---------------- Paths ----------------
BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR
STYLE_DIR = BASE_DIR / "Style"
IMAGES_DIR = BASE_DIR / "images"
UPLOADS_DIR = BASE_DIR / "uploads"

STYLE_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "pdf", "txt", "doc", "docx"}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# ---------------- Sessions ----------------
# IMPORTANT: change this in production
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


# ---------------- Optional OpenAI ----------------
# To enable real AI:
#   pip install openai
#   set OPENAI_API_KEY=YOUR_KEY   (Windows PowerShell: $env:OPENAI_API_KEY="YOUR_KEY")
#   export OPENAI_API_KEY=YOUR_KEY (Mac/Linux)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
oa_client = None
try:
    if OPENAI_API_KEY:
        from openai import OpenAI
        oa_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    oa_client = None


# ---------------- Helpers ----------------
def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def is_valid_id(s: str) -> bool:
    return isinstance(s, str) and s.isdigit() and len(s) == 8

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def record_paths(patient_id: str):
    patient_dir = UPLOADS_DIR / patient_id
    files_dir = patient_dir / "files"
    record_json = patient_dir / "record.json"
    return patient_dir, files_dir, record_json

def load_record(patient_id: str) -> dict:
    _, _, record_json = record_paths(patient_id)
    if record_json.exists():
        try:
            return json.loads(record_json.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_record(patient_id: str, data: dict):
    patient_dir, _, record_json = record_paths(patient_id)
    patient_dir.mkdir(parents=True, exist_ok=True)
    record_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def generate_patient_id() -> str:
    for _ in range(50):
        n = secrets.randbelow(90_000_000) + 10_000_000  # 8 digits
        pid = str(n)
        patient_dir, _, _ = record_paths(pid)
        if not patient_dir.exists():
            return pid
    return "12345678"

def ensure_guest_patient_id() -> str:
    """
    Ensures every visitor has a per-session 8-digit patient_id (guest mode),
    so MED CLOUD / MED SEARCH work without login or manual ID.
    """
    pid = (session.get("patient_id") or "").strip()
    if is_valid_id(pid):
        return pid

    pid = generate_patient_id()
    session["patient_id"] = pid
    session["role"] = session.get("role") or "guest"
    # create minimal record if not exists
    rec = load_record(pid)
    if not rec:
        rec = {"patient_id": pid, "symptoms": "", "files": [], "updated_at": now_iso()}
        save_record(pid, rec)
    return pid


# ---------------- HTML routes ----------------
@app.get("/")
def home():
    return send_from_directory(HTML_DIR, "index.html")

@app.get("/ar")
def home_ar():
    return send_from_directory(HTML_DIR, "arabic.html")

@app.get("/record")
def record_en():
    pid = (request.args.get("id") or "").strip()
    if not pid:
        pid = ensure_guest_patient_id()
        return redirect(f"/record?id={pid}")
    return send_from_directory(HTML_DIR, "record.html")

@app.get("/record_ar")
def record_ar():
    pid = (request.args.get("id") or "").strip()
    if not pid:
        pid = ensure_guest_patient_id()
        return redirect(f"/record_ar?id={pid}")
    return send_from_directory(HTML_DIR, "record_ar.html")

@app.get("/med_search")
def med_search():
    pid = (request.args.get("id") or "").strip()
    if not pid:
        pid = ensure_guest_patient_id()
        return redirect(f"/med_search?id={pid}")
    return send_from_directory(HTML_DIR, "med_search.html")

@app.get("/med_search_ar")
def med_search_ar():
    pid = (request.args.get("id") or "").strip()
    if not pid:
        pid = ensure_guest_patient_id()
        return redirect(f"/med_search_ar?id={pid}")
    return send_from_directory(HTML_DIR, "med_search_ar.html")

@app.get("/pain_3d")
def pain_3d():
    return send_from_directory(HTML_DIR, "pain_3d.html")

@app.get("/pain_3d_ar")
def pain_3d_ar():
    return send_from_directory(HTML_DIR, "pain_3d_ar.html")


# ---------------- Static folders ----------------
@app.get("/Style/<path:filename>")
def style_files(filename):
    return send_from_directory(STYLE_DIR, filename)

@app.get("/images/<path:filename>")
def images_files(filename):
    return send_from_directory(IMAGES_DIR, filename)

@app.get("/uploads/<path:filename>")
def uploads_files(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ---------------- API: Get Record ----------------
@app.get("/api/record/<patient_id>")
def api_get_record(patient_id):
    if not is_valid_id(patient_id):
        return jsonify({"ok": False, "error": "Invalid ID (must be 8 digits)."}), 400

    rec = load_record(patient_id)
    rec.setdefault("patient_id", patient_id)
    rec.setdefault("symptoms", "")
    rec.setdefault("files", [])
    rec.setdefault("updated_at", "")
    return jsonify({"ok": True, "record": rec})


# ---------------- API: Save Symptoms ----------------
@app.post("/api/record/<patient_id>/symptoms")
def api_save_symptoms(patient_id):
    if not is_valid_id(patient_id):
        return jsonify({"ok": False, "error": "Invalid ID (must be 8 digits)."}), 400

    payload = request.get_json(silent=True) or {}
    symptoms = (payload.get("symptoms") or "").strip()

    rec = load_record(patient_id)
    rec["patient_id"] = patient_id
    rec["symptoms"] = symptoms
    rec["files"] = rec.get("files", [])
    rec["updated_at"] = now_iso()

    save_record(patient_id, rec)
    return jsonify({"ok": True, "record": rec})
#this is a cchange

# ---------------- API: Upload Files ----------------
@app.post("/api/record/<patient_id>/upload")
def api_upload(patient_id):
    if not is_valid_id(patient_id):
        return jsonify({"ok": False, "error": "Invalid ID (must be 8 digits)."}), 400

    symptoms = (request.form.get("symptoms") or "").strip()
    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "error": "No files uploaded."}), 400

    patient_dir, files_dir, _ = record_paths(patient_id)
    files_dir.mkdir(parents=True, exist_ok=True)

    saved_meta = []
    for f in files:
        original = f.filename or ""
        safe = secure_filename(original)
        if not safe:
            continue
        if not allowed_file(safe):
            return jsonify({"ok": False, "error": f"File type not allowed: {original}"}), 400

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        final_name = f"{ts}__{safe}"
        save_path = files_dir / final_name
        f.save(save_path)

        saved_meta.append({
            "original": original,
            "stored": f"/uploads/{patient_id}/files/{final_name}",
            "size": save_path.stat().st_size,
            "type": (f.mimetype or "")
        })

    rec = load_record(patient_id)
    rec["patient_id"] = patient_id
    if symptoms:
        rec["symptoms"] = symptoms
    rec["files"] = (rec.get("files", []) + saved_meta)
    rec["updated_at"] = now_iso()
    save_record(patient_id, rec)

    return jsonify({"ok": True, "record": rec, "saved": saved_meta})


# ---------------- AI / Chat API ----------------
@app.post("/api/ask/<patient_id>")
def api_ask(patient_id):
    if not is_valid_id(patient_id):
        return jsonify({"ok": False, "error": "Invalid ID (must be 8 digits)."}), 400

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    symptoms = (payload.get("symptoms") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "Empty message."}), 400

    def fallback_answer(q: str, ctx: str) -> str:
        text = (q + " " + ctx).lower()

        emergency_flags = [
            "chest pain", "ضغط على الصدر", "ألم صدر", "ضيق نفس شديد", "severe shortness",
            "fainting", "اغماء", "stroke", "جلطة", "weakness one side", "ضعف جهة",
            "severe bleeding", "نزيف شديد", "suicid", "انتح"
        ]
        for k in emergency_flags:
            if k in text:
                return (
                    "⚠️ Urgent warning: your message may suggest an emergency.\n"
                    "Please seek emergency medical care immediately or call local emergency services.\n\n"
                    "This tool is information-only, not a diagnosis."
                )

        possibilities = []
        if any(k in text for k in ["fever", "حمى", "حرارة"]):
            possibilities.append("Infection / flu-like illness")
        if any(k in text for k in ["cough", "سعال", "كحة"]):
            possibilities.append("Respiratory infection / irritation")
        if any(k in text for k in ["headache", "صداع", "راس", "migraine", "شقيقة"]):
            possibilities.append("Headache (tension / migraine)")
        if any(k in text for k in ["stomach", "abdomen", "بطن", "معدة", "nausea", "غثيان"]):
            possibilities.append("Gastrointestinal issue (gastritis / food-related)")
        if any(k in text for k in ["rash", "طفح", "itch", "حكة"]):
            possibilities.append("Allergy / skin irritation")

        if not possibilities:
            possibilities = ["General symptom — needs more details"]

        questions = [
            "How long has this been happening?",
            "Do you have fever, shortness of breath, or severe pain?",
            "Any medications taken? Any chronic diseases?",
        ]
        return (
            "Initial guidance (demo):\n"
            f"- Possible categories: {', '.join(possibilities[:3])}\n\n"
            "Helpful questions to answer for a doctor:\n"
            f"- {questions[0]}\n- {questions[1]}\n- {questions[2]}\n\n"
            "✅ Note: This is not a diagnosis. If symptoms worsen or feel urgent, seek medical care."
        )

    if oa_client is None:
        return jsonify({"ok": True, "answer": fallback_answer(message, symptoms)})

    system_instructions = (
        "You are a medical information assistant for a student demo app. "
        "Do NOT provide a definitive diagnosis. Provide general information, likely possibilities, "
        "and advise seeing a licensed clinician. Ask 2-4 clarifying questions. "
        "If symptoms suggest emergency (chest pain, severe shortness of breath, stroke signs, "
        "severe bleeding, suicidal intent), tell the user to seek emergency care immediately. "
        "Keep answers short, clear, and safe."
    )

    user_prompt = (
        f"User question:\n{message}\n\n"
        f"User context/symptoms:\n{symptoms}\n"
    )

    try:
        resp = oa_client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
        )
        answer = getattr(resp, "output_text", None) or "No answer."
        return jsonify({"ok": True, "answer": answer})
    except Exception as e:
        return jsonify({"ok": True, "answer": fallback_answer(message, symptoms) + f"\n\n(AI error: {e})"})


# ---------------- Errors ----------------
@app.errorhandler(413)
def too_large(e):
    return jsonify({"ok": False, "error": "File too large. Max is 20MB."}), 413

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Not found."}), 404
    return "404 Not Found", 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
