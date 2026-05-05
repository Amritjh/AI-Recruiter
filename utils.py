import pdfplumber
import docx
import re
import sqlite3
import json
import os
from datetime import datetime

# ── Optional heavy deps ──────────────────────────────────────────────
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_OK = True
except Exception:
    SPACY_OK = False

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
    _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    ST_OK = True
except Exception:
    ST_OK = False

try:
    from rapidfuzz import fuzz
    FUZZ_OK = True
except Exception:
    FUZZ_OK = False

# ── Extended skill taxonomy ──────────────────────────────────────────
SKILL_LIST = [
    # Languages
    "python","java","c","c++","c#","go","rust","kotlin","swift","scala",
    "ruby","php","typescript","javascript","r","matlab","bash","shell",
    # Web
    "html","css","react","angular","vue","next.js","node.js","express",
    "django","flask","fastapi","spring","rails","graphql","rest api",
    "tailwind","bootstrap","sass",
    # Data / ML
    "sql","mysql","postgresql","mongodb","redis","elasticsearch",
    "machine learning","deep learning","nlp","computer vision",
    "data science","data analysis","pandas","numpy","scipy","matplotlib",
    "seaborn","scikit-learn","tensorflow","pytorch","keras","huggingface",
    "spark","hadoop","airflow","dbt","tableau","power bi","excel",
    # Cloud / DevOps
    "aws","azure","gcp","docker","kubernetes","terraform","ansible",
    "ci/cd","jenkins","github actions","linux","nginx","kafka",
    # Tools
    "git","github","gitlab","jira","confluence","figma","postman",
    "streamlit","jupyter","vscode","intellij",
]

SECTION_KEYWORDS = {
    "experience": ["experience","work history","employment","career","professional background"],
    "education":  ["education","academic","qualification","degree","university","college"],
    "skills":     ["skills","technical skills","competencies","technologies","tools"],
    "projects":   ["projects","portfolio","personal projects","academic projects"],
    "summary":    ["summary","objective","profile","about me","overview"],
}

DB_PATH = "recruiter.db"

# ─────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            location TEXT,
            skills TEXT,
            experience TEXT,
            description TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            name TEXT,
            email TEXT,
            phone TEXT,
            skills TEXT,
            education TEXT,
            experience_years REAL,
            raw_text TEXT,
            uploaded_at TEXT
        );
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            job_id INTEGER,
            ats_score INTEGER,
            similarity_score INTEGER,
            skill_score INTEGER,
            final_score INTEGER,
            missing_skills TEXT,
            status TEXT DEFAULT 'Pending',
            scored_at TEXT,
            UNIQUE(candidate_id, job_id)
        );
    """)
    con.commit()
    con.close()


def save_job(data: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO jobs (title,location,skills,experience,description,created_at)
        VALUES (?,?,?,?,?,?)
    """, (
        data["title"], data["location"],
        json.dumps(data["skills"]), data["experience"],
        data["description"], datetime.now().isoformat()
    ))
    con.commit()
    con.close()


def load_jobs():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id,title,location,skills,experience,description FROM jobs ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    jobs = []
    for r in rows:
        jobs.append({
            "id": r[0], "title": r[1], "location": r[2],
            "skills": json.loads(r[3]), "experience": r[4], "description": r[5]
        })
    return jobs


def save_candidate(data: dict) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO candidates
        (filename,name,email,phone,skills,education,experience_years,raw_text,uploaded_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data["filename"], data["name"], data["email"], data["phone"],
        json.dumps(data["skills"]), data.get("education",""),
        data.get("experience_years", 0),
        data["raw_text"], datetime.now().isoformat()
    ))
    con.commit()
    cid = cur.lastrowid
    con.close()
    return cid


def load_candidates():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id,filename,name,email,phone,skills,education,experience_years FROM candidates")
    rows = cur.fetchall()
    con.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0], "filename": r[1], "name": r[2], "email": r[3],
            "phone": r[4], "skills": json.loads(r[5]),
            "education": r[6], "experience_years": r[7]
        })
    return out


def save_score(candidate_id, job_id, scores: dict):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO scores
        (candidate_id,job_id,ats_score,similarity_score,skill_score,final_score,missing_skills,status,scored_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        candidate_id, job_id,
        scores["ats"], scores["similarity"], scores["skill"],
        scores["final"], json.dumps(scores["missing"]),
        scores.get("status","Pending"), datetime.now().isoformat()
    ))
    con.commit()
    con.close()


def update_status(candidate_id, job_id, status):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "UPDATE scores SET status=? WHERE candidate_id=? AND job_id=?",
        (status, candidate_id, job_id)
    )
    con.commit()
    con.close()


def load_ranked_candidates(job_id):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT c.id, c.name, c.email, c.phone, c.skills, c.education,
               c.experience_years, c.filename,
               s.ats_score, s.similarity_score, s.skill_score,
               s.final_score, s.missing_skills, s.status
        FROM scores s
        JOIN candidates c ON c.id = s.candidate_id
        WHERE s.job_id = ?
        ORDER BY s.final_score DESC
    """, (job_id,))
    rows = cur.fetchall()
    con.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0], "name": r[1], "email": r[2], "phone": r[3],
            "skills": json.loads(r[4]), "education": r[5],
            "experience_years": r[6], "filename": r[7],
            "ATS": r[8], "Similarity": r[9], "Skill Match": r[10],
            "Final Score": r[11],
            "Missing Skills": json.loads(r[12]) if r[12] else [],
            "Status": r[13]
        })
    return out

# ─────────────────────────────────────────────────────────────────────
# TEXT EXTRACTION
# ─────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception:
        pass
    return text


def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────────────
# SECTION SPLITTING
# ─────────────────────────────────────────────────────────────────────

def split_sections(text: str) -> dict:
    sections = {k: "" for k in SECTION_KEYWORDS}
    sections["other"] = ""
    lines = text.split("\n")
    current = "other"
    for line in lines:
        ll = line.lower().strip()
        matched = False
        for sec, kws in SECTION_KEYWORDS.items():
            if any(kw in ll for kw in kws) and len(ll) < 60:
                current = sec
                matched = True
                break
        if not matched:
            sections[current] += line + "\n"
    return sections

# ─────────────────────────────────────────────────────────────────────
# ENTITY EXTRACTION
# ─────────────────────────────────────────────────────────────────────

def extract_email(text: str) -> str:
    m = re.search(r"[\w.\+-]+@[\w.-]+\.\w{2,}", text)
    return m.group(0) if m else "Not Found"


def extract_phone(text: str) -> str:
    m = re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)
    return m.group(0).strip() if m else "Not Found"


def extract_name(text: str) -> str:
    if SPACY_OK:
        doc = nlp(text[:500])
        for ent in doc.ents:
            if ent.label_ == "PERSON" and 2 < len(ent.text) < 50:
                return ent.text.strip()
    # Fallback: first meaningful short line
    for line in text.split("\n")[:8]:
        line = line.strip()
        if 3 < len(line) < 45 and not any(c.isdigit() for c in line):
            return line
    return "Unknown"


def extract_education(text: str) -> str:
    edu_patterns = [
        r"(B\.?Tech|B\.?E\.?|Bachelor|B\.?Sc|M\.?Tech|M\.?E\.?|Master|M\.?Sc|MBA|Ph\.?D|Diploma)[^\n]{0,80}",
    ]
    found = []
    for pat in edu_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            found.append(m.group(0).strip())
    return " | ".join(found[:3]) if found else "Not Found"


def extract_experience_years(text: str) -> float:
    patterns = [
        r"(\d+\.?\d*)\s*\+?\s*years?\s+of\s+experience",
        r"experience\s+of\s+(\d+\.?\d*)\s*\+?\s*years?",
        r"(\d+\.?\d*)\s*\+?\s*yrs?\s+experience",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return 0.0


def extract_skills(text: str) -> list:
    found = []
    lower = text.lower()
    for skill in SKILL_LIST:
        if FUZZ_OK:
            # fuzzy: any 6-char window matching ≥88
            words = re.findall(r'\b[\w.#+]+\b', lower)
            if any(fuzz.ratio(skill, w) >= 88 for w in words):
                found.append(skill)
        else:
            if re.search(r'\b' + re.escape(skill) + r'\b', lower):
                found.append(skill)
    return list(dict.fromkeys(found))   # deduplicate, preserve order

# ─────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────

def calculate_skill_match(candidate_skills: list, required_skills: list):
    c = set(s.lower().strip() for s in candidate_skills)
    r = set(s.lower().strip() for s in required_skills)
    if not r:
        return 0, []
    if FUZZ_OK:
        matched = set()
        for rs in r:
            for cs in c:
                if fuzz.ratio(rs, cs) >= 80:
                    matched.add(rs)
                    break
    else:
        matched = c.intersection(r)
    score = int(len(matched) / len(r) * 100)
    missing = list(r - matched)
    return score, missing


def calculate_ats_score(skill_score: int, email: str, phone: str,
                         education: str, experience_years: float) -> int:
    score = skill_score
    if email != "Not Found":
        score += 5
    if phone != "Not Found":
        score += 5
    if education != "Not Found":
        score += 5
    if experience_years >= 1:
        score += min(int(experience_years) * 2, 10)
    return min(score, 100)


def calculate_similarity(job_text: str, resume_text: str) -> int:
    if not ST_OK or not job_text.strip() or not resume_text.strip():
        return 0
    a = _st_model.encode([job_text])
    b = _st_model.encode([resume_text[:3000]])   # cap for speed
    sim = sk_cosine(a, b)[0][0]
    return int(sim * 100)


def calculate_section_scores(job: dict, sections: dict) -> dict:
    """Score each resume section separately against the JD."""
    if not ST_OK:
        return {}
    jd = job["description"]
    out = {}
    for sec in ["experience", "skills", "education", "projects"]:
        txt = sections.get(sec, "").strip()
        if txt:
            a = _st_model.encode([jd])
            b = _st_model.encode([txt[:1000]])
            out[sec] = int(sk_cosine(a, b)[0][0] * 100)
        else:
            out[sec] = 0
    return out


def compute_final_score(ats: int, similarity: int) -> int:
    return int(ats * 0.6 + similarity * 0.4)


def parse_resume(file_path: str) -> dict:
    """Full pipeline: extract → split → analyse → return structured dict."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext in (".doc", ".docx"):
        text = extract_text_from_docx(file_path)
    else:
        return {}

    sections  = split_sections(text)
    name      = extract_name(text)
    email     = extract_email(text)
    phone     = extract_phone(text)
    skills    = extract_skills(text)
    education = extract_education(text)
    exp_years = extract_experience_years(text)

    return {
        "filename":        os.path.basename(file_path),
        "name":            name,
        "email":           email,
        "phone":           phone,
        "skills":          skills,
        "education":       education,
        "experience_years": exp_years,
        "sections":        sections,
        "raw_text":        text,
    }