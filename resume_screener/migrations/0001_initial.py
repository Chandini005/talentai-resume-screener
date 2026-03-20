"""Initial migration for AI Resume Screening System"""
from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import resume_screener.models


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False)),
                ('username', models.CharField(max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()])),
                ('first_name', models.CharField(blank=True, max_length=150)),
                ('last_name', models.CharField(blank=True, max_length=150)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('role', models.CharField(choices=[('recruiter', 'Recruiter'), ('candidate', 'Candidate')], default='candidate', max_length=20)),
                ('bio', models.TextField(blank=True, default='')),
                ('phone', models.CharField(blank=True, default='', max_length=20)),
                ('groups', models.ManyToManyField(blank=True, related_name='customuser_set', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='customuser_set', to='auth.permission')),
            ],
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
            managers=[('objects', django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name='JobPosting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('company', models.CharField(blank=True, default='', max_length=255)),
                ('location', models.CharField(blank=True, default='Remote', max_length=255)),
                ('description', models.TextField()),
                ('required_skills', models.TextField()),
                ('nice_to_have', models.TextField(blank=True, default='')),
                ('experience_level', models.CharField(choices=[('entry', 'Entry Level (0–2 yrs)'), ('mid', 'Mid Level (2–5 yrs)'), ('senior', 'Senior Level (5+ yrs)'), ('lead', 'Lead / Principal')], default='mid', max_length=20)),
                ('salary_range', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('recruiter', models.ForeignKey(limit_choices_to={'role': 'recruiter'}, on_delete=django.db.models.deletion.CASCADE, related_name='job_postings', to='resume_screener.customuser')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resume_file', models.FileField(upload_to=resume_screener.models.resume_upload_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'docx'])])),
                ('extracted_text', models.TextField(blank=True, default='')),
                ('match_score', models.FloatField(blank=True, null=True)),
                ('skill_score', models.FloatField(blank=True, null=True)),
                ('tfidf_score', models.FloatField(blank=True, null=True)),
                ('matched_skills', models.JSONField(blank=True, default=list)),
                ('missing_skills', models.JSONField(blank=True, default=list)),
                ('candidate_skills', models.JSONField(blank=True, default=list)),
                ('nlp_summary', models.TextField(blank=True, default='')),
                ('cover_letter', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('analysed', 'Analysed'), ('shortlisted', 'Shortlisted'), ('rejected', 'Rejected'), ('hired', 'Hired')], default='pending', max_length=20)),
                ('recruiter_notes', models.TextField(blank=True, default='')),
                ('applied_at', models.DateTimeField(auto_now_add=True)),
                ('analysed_at', models.DateTimeField(blank=True, null=True)),
                ('candidate', models.ForeignKey(limit_choices_to={'role': 'candidate'}, on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='resume_screener.customuser')),
                ('job_posting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='resume_screener.jobposting')),
            ],
            options={'ordering': ['-match_score', '-applied_at']},
        ),
        migrations.AddConstraint(
            model_name='application',
            constraint=models.UniqueConstraint(fields=['candidate', 'job_posting'], name='unique_candidate_per_job'),
        ),
    ]


# Fix missing import in migration
import django.core.validators
