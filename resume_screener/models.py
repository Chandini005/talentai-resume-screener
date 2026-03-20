"""
resume_screener/models.py

Models:
  CustomUser   — extended user with Recruiter / Candidate roles
  JobPosting   — job created by a recruiter
  Application  — candidate applies to a job; stores NLP analysis results
"""

import json
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM USER
# ─────────────────────────────────────────────────────────────────────────────

class CustomUser(AbstractUser):
    """Single user model for both Recruiters and Candidates."""

    class Role(models.TextChoices):
        RECRUITER = 'recruiter', 'Recruiter'
        CANDIDATE = 'candidate', 'Candidate'

    role  = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)
    bio   = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')

    def is_recruiter(self):
        return self.role == self.Role.RECRUITER

    def is_candidate(self):
        return self.role == self.Role.CANDIDATE

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


# ─────────────────────────────────────────────────────────────────────────────
# JOB POSTING
# ─────────────────────────────────────────────────────────────────────────────

class JobPosting(models.Model):
    """A position created by a Recruiter."""

    class ExperienceLevel(models.TextChoices):
        ENTRY  = 'entry',  'Entry Level (0–2 yrs)'
        MID    = 'mid',    'Mid Level (2–5 yrs)'
        SENIOR = 'senior', 'Senior Level (5+ yrs)'
        LEAD   = 'lead',   'Lead / Principal'

    recruiter       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_postings',
        limit_choices_to={'role': 'recruiter'},
    )
    title           = models.CharField(max_length=255)
    company         = models.CharField(max_length=255, blank=True, default='')
    location        = models.CharField(max_length=255, blank=True, default='Remote')
    description     = models.TextField(help_text='Full job description sent to NLP engine.')
    required_skills = models.TextField(help_text='Comma-separated required skills.')
    nice_to_have    = models.TextField(blank=True, default='', help_text='Optional / bonus skills.')
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.MID,
    )
    salary_range    = models.CharField(max_length=100, blank=True, default='')
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} @ {self.company or "N/A"}'

    def get_required_skills_list(self):
        """Returns required_skills as a clean Python list."""
        return [s.strip() for s in self.required_skills.split(',') if s.strip()]

    def get_nice_to_have_list(self):
        return [s.strip() for s in self.nice_to_have.split(',') if s.strip()]

    @property
    def applicant_count(self):
        return self.applications.count()

    @property
    def shortlisted_count(self):
        return self.applications.filter(match_score__gte=70).count()


# ─────────────────────────────────────────────────────────────────────────────
# RESUME UPLOAD PATH
# ─────────────────────────────────────────────────────────────────────────────

def resume_upload_path(instance, filename):
    """Organise uploads: media/resumes/job_<id>/<username>/<filename>"""
    return f'resumes/job_{instance.job_posting.id}/{instance.candidate.username}/{filename}'


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class Application(models.Model):
    """
    A candidate's application to a JobPosting.

    NLP pipeline writes:
      extracted_text   — raw text from PDF/DOCX
      match_score      — 0-100 overall similarity
      matched_skills   — JSON list of found skills
      missing_skills   — JSON list of absent skills
      skill_score      — skill overlap sub-score
      tfidf_score      — TF-IDF cosine similarity sub-score
      nlp_summary      — plain-text feedback paragraph
    """

    class Status(models.TextChoices):
        PENDING     = 'pending',     'Pending'
        ANALYSED    = 'analysed',    'Analysed'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        REJECTED    = 'rejected',    'Rejected'
        HIRED       = 'hired',       'Hired'

    # ── Relationships ─────────────────────────────────────────────────────
    candidate   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        limit_choices_to={'role': 'candidate'},
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='applications',
    )

    # ── File ──────────────────────────────────────────────────────────────
    resume_file = models.FileField(
        upload_to=resume_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx'])],
    )

    # ── NLP Output ────────────────────────────────────────────────────────
    extracted_text  = models.TextField(blank=True, default='')
    match_score     = models.FloatField(null=True, blank=True)   # 0.0 – 100.0
    skill_score     = models.FloatField(null=True, blank=True)   # 0.0 – 100.0
    tfidf_score     = models.FloatField(null=True, blank=True)   # 0.0 – 100.0
    matched_skills  = models.JSONField(default=list, blank=True) # ["Python","Django"]
    missing_skills  = models.JSONField(default=list, blank=True)
    candidate_skills = models.JSONField(default=list, blank=True)
    nlp_summary     = models.TextField(blank=True, default='')

    # ── Candidate-supplied fields ──────────────────────────────────────────
    cover_letter    = models.TextField(blank=True, default='')

    # ── Status & timestamps ───────────────────────────────────────────────
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    recruiter_notes = models.TextField(blank=True, default='')
    applied_at      = models.DateTimeField(auto_now_add=True)
    analysed_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-match_score', '-applied_at']
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'job_posting'],
                name='unique_candidate_per_job'
            )
        ]

    def __str__(self):
        score = f'{self.match_score:.1f}%' if self.match_score is not None else 'Pending'
        return f'{self.candidate.username} → {self.job_posting.title} [{score}]'

    # ── Score helpers ─────────────────────────────────────────────────────
    @property
    def score_label(self):
        if self.match_score is None:
            return 'Pending'
        if self.match_score >= 80:
            return 'Excellent'
        if self.match_score >= 65:
            return 'Good'
        if self.match_score >= 45:
            return 'Fair'
        return 'Low'

    @property
    def score_color(self):
        """CSS colour token for template badges."""
        if self.match_score is None:
            return 'secondary'
        if self.match_score >= 70:
            return 'success'
        if self.match_score >= 45:
            return 'warning'
        return 'danger'

    @property
    def is_shortlisted(self):
        return self.match_score is not None and self.match_score >= 70

    def mark_analysed(self):
        self.status = self.Status.ANALYSED
        self.analysed_at = timezone.now()
