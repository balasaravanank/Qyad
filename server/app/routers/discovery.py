"""Private preferences and a bounded, keyless public-feed adapter.
Never send resume text, target roles or account identifiers to a job provider.
"""
import html
import json
import re
import threading
import time
import subprocess
import sys
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user, write_audit
from ..models import User, MatchProfile, Opportunity, Application
from ..serializers import opportunity_json, application_json
from .opportunities import clean_url

router = APIRouter(prefix="/api", tags=["discovery"])
SOURCE_URL = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_HOME = "https://www.arbeitnow.com"
CACHE_SECONDS = 3600
_cache = {"jobs": [], "fetched_at": None, "attempted_at": 0, "error": None}
_lock = threading.Lock()
SKILLS = {"python", "java", "javascript", "typescript", "react", "angular", "vue", "node", "node.js", "fastapi", "django", "flask", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux", "html", "css", "figma", "excel", "tableau", "pytorch", "tensorflow", "pandas", "numpy", "golang", "rust", "c++", "c#", ".net", "flutter", "kotlin", "swift", "graphql", "livekit", "webrtc", "whisper", "deepgram", "langgraph", "langchain", "llm", "stt", "tts", "terraform", "fastapi"}
STOP = {"and", "or", "the", "a", "an", "for", "of", "in", "to", "with", "role", "roles"}


def words(text):
    return [t.rstrip(".-") for t in re.findall(r"[a-z0-9][a-z0-9.+#-]*|\.net", (text or "").lower())]


def profile_terms(profile):
    if not profile:
        return []
    explicit = [w.strip().lower() for w in re.split(r"[,;\n]", profile.keywords or "") if w.strip()]
    role_words = [w for w in words(profile.roles) if w not in STOP and len(w) > 1]
    resume_words = set(words(profile.resume_text))
    return sorted(set(explicit + role_words + sorted(SKILLS & resume_words)))[:60]


def match(terms, text):
    tokens = set(words(text))
    normalized = " ".join(words(text))
    return [t for t in terms if (t in tokens if " " not in t else t in normalized)]


class ProfileIn(BaseModel):
    roles: str = Field(default="", max_length=1000)
    keywords: str = Field(default="", max_length=3000)
    resume_text: str = Field(default="", max_length=40000)


def profile_json(p):
    return {"roles": p.roles if p else "", "keywords": p.keywords if p else "",
            "resume_text": p.resume_text if p else "", "terms": profile_terms(p)}


@router.get("/match-profile")
def get_profile(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    return profile_json(db.get(MatchProfile, user.id))


@router.put("/match-profile")
def put_profile(data: ProfileIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    p = db.get(MatchProfile, user.id)
    if not p:
        p = MatchProfile(user_id=user.id)
        db.add(p)
    p.roles, p.keywords, p.resume_text = data.roles, data.keywords, data.resume_text
    db.commit()
    return profile_json(p)


@router.post("/match-profile/resume-preview")
async def resume_preview(file: UploadFile = File(...), user: User = Depends(current_user)):
    raw = await file.read(2_000_001)
    await file.close()
    if not raw or len(raw) > 2_000_000:
        raise HTTPException(413, "Use a non-empty PDF or TXT file under 2 MB")
    name = (file.filename or "").lower()
    if name.endswith('.txt'):
        try:
            text = raw.decode('utf-8-sig')[:40000]
        except UnicodeDecodeError:
            raise HTTPException(400, 'TXT must use UTF-8 encoding')
    elif name.endswith('.pdf') and raw.startswith(b'%PDF-'):
        # A separate bounded process handles untrusted PDF content. Nothing is executed from the PDF.
        import asyncio
        def extract():
            return subprocess.run([sys.executable, '-m', 'app.resume_worker'], input=raw,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8, check=True)
        try:
            result = await asyncio.to_thread(extract)
            parsed = json.loads(result.stdout)
            if parsed.get('error'):raise ValueError('parse')
            text = parsed['text']
        except Exception:
            raise HTTPException(400, 'PDF could not be read within safe limits. Use an unencrypted text PDF, at most 20 pages, or paste the text.')
    else:
        raise HTTPException(415, 'Supported files: text-based PDF and UTF-8 TXT. No DOCX or images yet.')
    if len(text.strip()) < 30:
        raise HTTPException(422, 'No usable text found. Scanned PDFs need OCR first; paste the text instead.')
    skills = sorted(SKILLS & set(words(text)))
    return {"resume_text": text, "skills": skills,
        "notice": "Parsed on this server only. Original file is not saved. Review the text and skills, then Save profile to store them privately. No resume data is sent to job providers or an AI service."}


def match_explanation(terms, job):
    text = ' '.join([job['title'], job['description'], job['company']])
    hits = match(terms, text)
    weights = {term: (3 if term in SKILLS else 1) for term in terms}
    score = round(100 * sum(weights[t] for t in hits) / sum(weights.values())) if weights else None
    job_skills = SKILLS & set(words(text))
    missing = sorted(job_skills - set(terms))
    return {"matched_terms": hits, "match_count": len(hits), "match_score": score,
        "missing_skills": missing, "score_method": "Profile-term coverage: known technical skills weight 3, other role/keyword terms weight 1. Not hiring probability or eligibility verification."}


def text_only(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", str(value or "")))).strip()


def normalize_jobs(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Unexpected feed format")
    result, seen = [], set()
    for raw in payload["data"][:400]:
        if not isinstance(raw, dict):
            continue
        try:
            if not isinstance(raw.get("url"), str):
                continue
            url = clean_url(raw.get("url"))
            # Keep attribution links on the actual provider, never an injected scheme or unrelated host.
            if not url or not url.startswith(("https://www.arbeitnow.com/", "https://arbeitnow.com/")):
                continue
            slug = str(raw.get("slug") or "")[:300]
            title = text_only(raw.get("title"))[:500]
            if not title or not slug or slug in seen:
                continue
            seen.add(slug)
            created = datetime.fromtimestamp(int(raw.get("created_at") or 0), timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError, OSError):
            continue
        desc = text_only(raw.get("description"))[:16000]
        result.append({"id": slug, "title": title, "company": text_only(raw.get("company_name"))[:500],
            "url": url, "location": text_only(raw.get("location"))[:500], "remote": raw.get("remote") is True,
            "description": desc, "created_at": created, "deadline": None,
            "kind": "internship" if any(w in title.lower() for w in ("intern", "praktik", "trainee")) else "job",
            "source": "Arbeitnow"})
    return result


def fetch_public_jobs():
    request = Request(SOURCE_URL, headers={"User-Agent": "StudentQyadPersonal/0.3", "Accept": "application/json"})
    with urlopen(request, timeout=8) as response:
        raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError("Feed too large")
    return normalize_jobs(json.loads(raw))


def feed():
    with _lock:
        if time.monotonic() - _cache["attempted_at"] >= CACHE_SECONDS or not _cache["attempted_at"]:
            _cache["attempted_at"] = time.monotonic()
            try:
                _cache["jobs"] = fetch_public_jobs()
                _cache["fetched_at"] = datetime.now(timezone.utc).isoformat()
                _cache["error"] = None
            except Exception:
                # Retain a prior successful response. Do not expose provider bodies or internal errors.
                _cache["error"] = "Arbeitnow is unavailable right now. Try again after the hourly cache refresh."
        return {"jobs": list(_cache["jobs"]), "fetched_at": _cache["fetched_at"], "error": _cache["error"]}


def curated_jobs():
    # This is a dated editorial snapshot, not an automated open-status checker.
    rows = json.loads((Path(__file__).parents[1] / "data" / "opportunities.json").read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).date()
    for row in rows:
        age = (today - date.fromisoformat(row["checked_at"])).days
        row["stale"] = age > 14
        row["expired"] = bool(row.get("deadline") and row["deadline"] < today.isoformat()) or bool(row.get("event_end") and row["event_end"] < today.isoformat())
    return [r for r in rows if not r["expired"]]


@router.get("/discover")
def discover(source: str = "live", user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    if source not in ("curated", "live"):
        raise HTTPException(400, "Unknown discovery source")
    result = ({"jobs": curated_jobs(), "fetched_at": None, "error": None} if source == "curated" else feed())
    terms = profile_terms(db.get(MatchProfile, user.id))
    jobs = []
    for job in result["jobs"]:
        jobs.append({**job, **match_explanation(terms, job)})
    jobs.sort(key=lambda j: (j.get("match_score") or 0, j["match_count"], j["created_at"]), reverse=True)
    if source == "curated":
        return {**result, "jobs": jobs, "terms": terms, "source_url": None, "source": "curated",
            "coverage": "India-first internships and student hackathons. Source pages checked 23 Nov 2026. This is a dated shortlist, not a continuously verified feed. Open the source to confirm status, eligibility and deadlines. Older than 14 days is marked for recheck; known past deadlines are hidden.", "cache_minutes": 0}
    return {**result, "jobs": jobs, "terms": terms, "source": "live", "source_url": SOURCE_HOME,
        "coverage": "Arbeitnow's latest first page only, mainly Europe. India internships may be scarce. Remote does not mean eligible everywhere. Deadlines are not supplied. Verify every listing on its source page.",
        "cache_minutes": 60}


class SaveIn(BaseModel):
    space_id: str | None = None


@router.post("/discover/{job_id}/save")
def save_job(job_id: str, data: SaveIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    # Validate destination before consulting the public feed.
    if data.space_id:
        space = get_space_for_user(db, data.space_id, user)
        if space.type == "personal":
            raise HTTPException(400, "Use private tracking for personal finds")
    job = next((j for j in curated_jobs() if j["id"] == job_id), None)
    if not job:
        job = next((j for j in feed()["jobs"] if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Listing is no longer in the current feed. Open the source page to check it.")
    attribution = f"Source: {job['source']}. {job['url']}\nLocation: {job['location']}. {job.get('description', '')[:1600]}\nVerify current status, eligibility and deadline on the source."
    deadline = date.fromisoformat(job["deadline"]) if job.get("deadline") else None
    if data.space_id:
        existing = db.query(Opportunity).filter(Opportunity.space_id == data.space_id, Opportunity.url == job["url"]).first()
        if existing:
            return {"opportunity": opportunity_json(existing), "already_saved": True}
        obj = Opportunity(space_id=data.space_id, posted_by=user.id, title=job["title"],
            company=job["company"], url=job["url"], kind=job["kind"], description=attribution, deadline=deadline)
        db.add(obj); db.flush()
        write_audit(db, "user", user.id, "create", "opportunities", obj.id, after=opportunity_json(obj))
        db.commit()
        return {"opportunity": opportunity_json(obj)}
    existing = db.query(Application).filter(Application.user_id == user.id, Application.url == job["url"]).first()
    if existing:
        return {"application": application_json(existing), "already_saved": True}
    obj = Application(user_id=user.id, title=job["title"], company=job["company"], url=job["url"], notes=attribution, deadline=deadline, status="saved")
    db.add(obj); db.flush()
    write_audit(db, "user", user.id, "create", "applications", obj.id, after=application_json(obj))
    db.commit()
    return {"application": application_json(obj)}
