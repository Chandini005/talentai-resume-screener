"""resume_screener/admin.py"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, JobPosting, Application


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_active')
    search_fields = ('username', 'email')
    fieldsets     = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role', 'bio', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display  = ('title', 'company', 'recruiter', 'is_active', 'applicant_count', 'created_at')
    list_filter   = ('is_active', 'experience_level')
    search_fields = ('title', 'company', 'required_skills')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ('candidate', 'job_posting', 'match_score', 'skill_score',
                     'tfidf_score', 'status', 'applied_at')
    list_filter   = ('status', 'job_posting')
    search_fields = ('candidate__username', 'job_posting__title')
    ordering      = ('-match_score',)
    readonly_fields = ('extracted_text', 'match_score', 'skill_score', 'tfidf_score',
                       'matched_skills', 'missing_skills', 'candidate_skills',
                       'nlp_summary', 'applied_at', 'analysed_at')
