"""resume_screener/views.py"""

import logging
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ApplicationForm, JobPostingForm, LoginForm, RecruiterNotesForm, RegisterForm
from .models import Application, CustomUser, JobPosting
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from . import nlp_engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# ACCESS CONTROL DECORATORS
# ─────────────────────────────────────────────────────────────────────────────

def recruiter_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_recruiter():
            raise PermissionDenied
        return fn(request, *args, **kwargs)
    return wrapper


def candidate_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_candidate():
            raise PermissionDenied
        return fn(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name or user.username}! Account created.')
            return redirect('dashboard')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'resume_screener/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                return redirect(request.GET.get('next', 'dashboard'))
            messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = LoginForm()
    return render(request, 'resume_screener/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Smart router — sends user to the correct role dashboard."""
    if request.user.is_recruiter():
        return redirect('recruiter_dashboard')
    return redirect('candidate_dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# RECRUITER VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@recruiter_required
def recruiter_dashboard(request):
    jobs = (
        JobPosting.objects
        .filter(recruiter=request.user)
        .annotate(
            total_applicants=Count('applications'),
            avg_score=Avg('applications__match_score'),
        )
        .order_by('-created_at')
    )
    total_applicants = sum(j.total_applicants for j in jobs)
    shortlisted      = Application.objects.filter(
        job_posting__recruiter=request.user,
        match_score__gte=70,
    ).count()

    return render(request, 'resume_screener/recruiter_dashboard.html', {
        'jobs':             jobs,
        'total_jobs':       jobs.count(),
        'active_jobs':      jobs.filter(is_active=True).count(),
        'total_applicants': total_applicants,
        'shortlisted':      shortlisted,
    })


@login_required
@recruiter_required
def job_create(request):
    if request.method == 'POST':
        form = JobPostingForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.recruiter = request.user
            job.save()
            messages.success(request, f'Job "{job.title}" posted successfully!')
            return redirect('job_applicants', job_id=job.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = JobPostingForm()
    return render(request, 'resume_screener/job_create.html', {'form': form, 'editing': False})


@login_required
@recruiter_required
def job_edit(request, job_id):
    job = get_object_or_404(JobPosting, pk=job_id, recruiter=request.user)
    if request.method == 'POST':
        form = JobPostingForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job posting updated.')
            return redirect('job_applicants', job_id=job.pk)
    else:
        form = JobPostingForm(instance=job)
    return render(request, 'resume_screener/job_create.html', {'form': form, 'editing': True, 'job': job})


@login_required
@recruiter_required
def job_applicants(request, job_id):
    """
    The core recruiter dashboard — ranked applicant table with NLP scores.
    """
    job = get_object_or_404(JobPosting, pk=job_id, recruiter=request.user)

    # Filter parameter
    min_score  = request.GET.get('min_score', '')
    status_filter = request.GET.get('status', '')

    applications = (
        Application.objects
        .filter(job_posting=job)
        .select_related('candidate')
        .order_by('-match_score', '-applied_at')
    )

    if min_score:
        try:
            applications = applications.filter(match_score__gte=float(min_score))
        except ValueError:
            pass

    if status_filter:
        applications = applications.filter(status=status_filter)

    # Stats
    all_apps   = job.applications.all()
    avg_score  = all_apps.aggregate(avg=Avg('match_score'))['avg'] or 0
    shortlisted = all_apps.filter(match_score__gte=70).count()

    return render(request, 'resume_screener/job_applicants.html', {
        'job':           job,
        'applications':  applications,
        'total':         all_apps.count(),
        'avg_score':     round(avg_score, 1),
        'shortlisted':   shortlisted,
        'min_score':     min_score,
        'status_filter': status_filter,
        'status_choices': Application.Status.choices,
    })


@login_required
@recruiter_required
def application_detail(request, app_id):
    """Full detail view for one application — shows NLP summary, skills, resume link."""
    app = get_object_or_404(
        Application.objects.select_related('candidate', 'job_posting'),
        pk=app_id,
        job_posting__recruiter=request.user,
    )
    notes_form = RecruiterNotesForm(instance=app)

    if request.method == 'POST':
        notes_form = RecruiterNotesForm(request.POST, instance=app)
        if notes_form.is_valid():
            notes_form.save()
            messages.success(request, 'Application status updated.')
            return redirect('application_detail', app_id=app.pk)

    return render(request, 'resume_screener/application_detail.html', {
        'app':        app,
        'notes_form': notes_form,
        'status_choices': Application.Status.choices,
    })


@login_required
@recruiter_required
def recruiter_applications_all(request):
    """View all applications across all jobs for a recruiter."""
    # Filter parameters
    min_score = request.GET.get('min_score', '')
    status_filter = request.GET.get('status', '')
    
    apps = (
        Application.objects
        .filter(job_posting__recruiter=request.user)
        .select_related('candidate', 'job_posting')
        .order_by('-applied_at')
    )
    
    if min_score:
        try:
            apps = apps.filter(match_score__gte=float(min_score))
        except ValueError:
            pass
            
    if status_filter:
        apps = apps.filter(status=status_filter)
        
    return render(request, 'resume_screener/recruiter_applications_all.html', {
        'applications': apps,
        'min_score': min_score,
        'status_filter': status_filter,
        'status_choices': Application.Status.choices,
    })


# ─────────────────────────────────────────────────────────────────────────────
# CANDIDATE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@candidate_required
def candidate_dashboard(request):
    applied_job_ids = set(
        Application.objects.filter(candidate=request.user)
        .values_list('job_posting_id', flat=True)
    )
    jobs = (
        JobPosting.objects.filter(is_active=True)
        .select_related('recruiter')
        .order_by('-created_at')
    )

    jobs_data = [
        {
            'job': j,
            'applied': j.pk in applied_job_ids,
            'skills': j.get_required_skills_list(),
        }
        for j in jobs
    ]

    return render(request, 'resume_screener/candidate_dashboard.html', {
        'jobs_data':  jobs_data,
        'open_count': jobs.count(),
    })


@login_required
@candidate_required
def apply_job(request, job_id):
    """Upload resume → trigger NLP pipeline → save scores."""
    job = get_object_or_404(JobPosting, pk=job_id, is_active=True)

    if Application.objects.filter(candidate=request.user, job_posting=job).exists():
        messages.warning(request, f'You have already applied for "{job.title}".')
        return redirect('my_applications')

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Save the application record (file written to disk)
            app = form.save(commit=False)
            app.candidate   = request.user
            app.job_posting = job
            app.save()

            # 2. Run NLP pipeline
            try:
                result = nlp_engine.analyse(app.resume_file.path, job)

                app.extracted_text   = result['extracted_text']
                app.match_score      = result['match_score']
                app.skill_score      = result['skill_score']
                app.tfidf_score      = result['tfidf_score']
                app.matched_skills   = result['matched_skills']
                app.missing_skills   = result['missing_skills']
                app.candidate_skills = result['candidate_skills']
                app.nlp_summary      = result['nlp_summary']
                app.mark_analysed()
                app.save()

                if result.get('error'):
                    messages.warning(request, f'Applied, but NLP note: {result["error"]}')
                else:
                    messages.success(
                        request,
                        f'Application submitted! Your AI match score: {app.match_score:.1f}%'
                    )
            except Exception as e:
                logger.error("NLP pipeline failed for application #%d: %s", app.pk, e, exc_info=True)
                messages.warning(request, 'Application saved, but AI analysis encountered an error.')

            return redirect('my_applications')
        messages.error(request, 'Please fix the form errors.')
    else:
        form = ApplicationForm()

    return render(request, 'resume_screener/apply.html', {
        'form': form,
        'job':  job,
        'skills': job.get_required_skills_list(),
    })


@login_required
@candidate_required
def my_applications(request):
    applications = (
        Application.objects.filter(candidate=request.user)
        .select_related('job_posting', 'job_posting__recruiter')
        .order_by('-applied_at')
    )
    return render(request, 'resume_screener/my_applications.html', {
        'applications': applications,
        'total':        applications.count(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# SHARED / UTILITY VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    total_jobs  = JobPosting.objects.filter(is_active=True).count()
    total_apps  = Application.objects.filter(status='analysed').count()
    return render(request, 'resume_screener/landing.html', {
        'total_jobs': total_jobs,
        'total_apps': total_apps,
    })


def handler403(request, exception=None):
    return render(request, 'resume_screener/403.html', status=403)


def handler404(request, exception=None):
    return render(request, 'resume_screener/404.html', status=404)


@login_required
@recruiter_required
def download_analysis_pdf(request, app_id):
    """Generate a professional PDF report of the candidate analysis."""
    app = get_object_or_404(
        Application.objects.select_related('candidate', 'job_posting'),
        pk=app_id,
        job_posting__recruiter=request.user,
    )
    
    template_path = 'resume_screener/analysis_report.html'
    context = {'app': app, 'today': timezone.now()}
    
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="analysis_{app.candidate.username}.pdf"'
    
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response)
       
    # if error then show some funny view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


@login_required
@recruiter_required
def update_application_status(request, app_id):
    """Update the pipeline status of an application."""
    if request.method == 'POST':
        app = get_object_or_404(Application, pk=app_id, job_posting__recruiter=request.user)
        new_status = request.POST.get('status')
        if new_status in Application.Status.values:
            app.status = new_status
            app.save()
            messages.success(request, f'Status updated to {app.get_status_display()}')
        return redirect('application_detail', app_id=app.pk)
    return redirect('dashboard')
