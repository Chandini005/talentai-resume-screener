# TalentAI — AI-Based Resume Screening System

A complete, production-structured Django application that screens resumes against job descriptions using **local NLP** — no API keys, no external services required.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 |
| Database | SQLite (swap to PostgreSQL for production) |
| PDF Parsing | pdfplumber |
| DOCX Parsing | python-docx |
| NLP / AI | NLTK · scikit-learn (TF-IDF) |
| Skill Detection | Custom 100+ skill vocabulary + regex |
| Semantic Scoring | TF-IDF cosine similarity |
| Frontend | Bootstrap 5 + Bootstrap Icons (CDN) |
| Auth | Django built-in + custom user roles |

---

## Project Structure

```
resume_ai_system/
│
├── config/                          # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── resume_screener/                 # Main application
│   ├── models.py                    # CustomUser, JobPosting, Application
│   ├── views.py                     # All 12 views
│   ├── forms.py                     # Register, Login, Job, Application forms
│   ├── urls.py                      # 14 URL patterns
│   ├── admin.py                     # Admin panel config
│   ├── nlp_engine.py                # ← The full NLP pipeline
│   │
│   ├── migrations/
│   │   └── 0001_initial.py
│   │
│   └── templates/resume_screener/
│       ├── base.html                # Master layout (dark editorial theme)
│       ├── landing.html             # Public homepage
│       ├── login.html
│       ├── register.html
│       ├── recruiter_dashboard.html # Job list + stats
│       ├── job_create.html          # Create / edit job
│       ├── job_applicants.html      # ← Ranked applicant table (core view)
│       ├── application_detail.html  # Full NLP breakdown
│       ├── candidate_dashboard.html # Browse jobs
│       ├── apply.html               # Upload resume
│       ├── my_applications.html     # Candidate's score history
│       ├── 403.html
│       └── 404.html
│
├── media/resumes/                   # Uploaded files (git-ignored)
├── manage.py
├── requirements.txt
├── setup.sh                         # One-command setup
└── README.md
```

---

## Quickstart

### Option A — Automated (recommended)

```bash
bash setup.sh
```

### Option B — Manual

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download NLTK language data
python -c "
import nltk
for pkg in ['stopwords','wordnet','punkt','punkt_tab','averaged_perceptron_tagger']:
    nltk.download(pkg, quiet=True)
"

# 4. Apply database migrations
python manage.py migrate

# 5. Create admin account
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## User Roles

| Role | What they can do |
|---|---|
| **Recruiter** | Post jobs · View ranked applicants · Update status · Read NLP reports |
| **Candidate** | Browse jobs · Upload resume (PDF/DOCX) · See AI match score · Track applications |

Register at `/register/` and choose your role. Both roles use the same registration form.

---

## The NLP Pipeline (`nlp_engine.py`)

When a candidate uploads a resume, this 8-step pipeline runs synchronously:

```
1. extract_text()
   └─ pdfplumber (PDF) or python-docx (DOCX) → raw string

2. extract_candidate_info()
   └─ Regex heuristics → name, email, phone, years of experience

3. preprocess()
   └─ NLTK: lowercase → remove URLs/emails → tokenise
      → remove stopwords → lemmatise (WordNetLemmatizer)

4. extract_skills()
   └─ Match 100+ skills from SKILL_VOCAB against resume text
      using word-boundary regex (avoids partial matches)

5. skill_overlap_score()
   └─ candidate_skills ∩ required_skills → matched / missing
      Score = (matched / required) × 100

6. tfidf_similarity()
   └─ TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)
      Cosine similarity between resume and job description vectors

7. calculate_final_score()
   └─ match_score = (skill_score × 0.60) + (tfidf_score × 0.40)

8. generate_summary()
   └─ Plain-English paragraph summarising the analysis
```

### Scoring Formula

```
Final Score = (Skill Overlap × 60%) + (TF-IDF Semantic × 40%)
```

- **Skill Overlap (60%)** — direct match between resume skills and job requirements
- **TF-IDF Semantic (40%)** — how contextually relevant the resume is to the full JD

### Shortlisting threshold

Candidates scoring **≥ 70%** are automatically flagged as shortlisted in the recruiter dashboard.

---

## URL Reference

| URL | View | Auth |
|---|---|---|
| `/` | Landing page | Public |
| `/register/` | Registration | Public |
| `/login/` | Login | Public |
| `/dashboard/` | Role-based router | Login |
| `/recruiter/` | Recruiter dashboard | Recruiter |
| `/jobs/new/` | Create job | Recruiter |
| `/jobs/<id>/edit/` | Edit job | Recruiter (owner) |
| `/jobs/<id>/applicants/` | Ranked applicants | Recruiter (owner) |
| `/applications/<id>/` | Application detail | Recruiter (owner) |
| `/candidate/` | Browse jobs | Candidate |
| `/jobs/<id>/apply/` | Upload resume | Candidate |
| `/my-applications/` | My scores | Candidate |
| `/admin/` | Django admin | Superuser |

---

## Skill Vocabulary

The NLP engine detects **100+ skills** across these categories:

- Programming: Python, Java, JavaScript, TypeScript, Go, Rust, C++, C#, Swift, Kotlin…
- Web: React, Angular, Vue, Django, FastAPI, Node.js, Next.js, GraphQL…
- Databases: PostgreSQL, MongoDB, Redis, Elasticsearch, MySQL, SQLite…
- Cloud/DevOps: AWS, Azure, GCP, Docker, Kubernetes, Terraform, CI/CD…
- Data/ML: TensorFlow, PyTorch, scikit-learn, Pandas, NLP, Computer Vision…
- Mobile: Android, iOS, React Native, Flutter…
- Soft skills: Leadership, Agile, Scrum, Communication…

To add custom skills, edit the `SKILL_VOCAB` set in `nlp_engine.py`.

---

## Production Checklist

- [ ] Set `DEBUG = False` in `settings.py`
- [ ] Replace `SECRET_KEY` with a secure random value
- [ ] Switch to PostgreSQL (`psycopg2-binary`)
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Serve media files via Nginx or S3
- [ ] Run `python manage.py collectstatic`
- [ ] Use `gunicorn` instead of the dev server

---

## Admin Panel

Access at `/admin/` with your superuser credentials.

All models are registered with:
- Full read/write for `CustomUser`, `JobPosting`, `Application`
- NLP result fields are read-only (populated by the pipeline, not manually)
- `Application` list is sorted by `match_score` descending

---

Built with Django · NLTK · scikit-learn · pdfplumber · Bootstrap 5
