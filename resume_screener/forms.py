"""resume_screener/forms.py"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, JobPosting, Application


class RegisterForm(UserCreationForm):
    email     = forms.EmailField(required=True)
    role      = forms.ChoiceField(choices=CustomUser.Role.choices)
    first_name = forms.CharField(max_length=50, required=False)
    last_name  = forms.CharField(max_length=50, required=False)

    class Meta:
        model  = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2')

    def _apply_class(self, field_name, css='form-control'):
        self.fields[field_name].widget.attrs.update({'class': css})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.update({'class': css})

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email      = self.cleaned_data['email']
        user.role       = self.cleaned_data['role']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name  = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))


class JobPostingForm(forms.ModelForm):
    class Meta:
        model  = JobPosting
        fields = ('title', 'company', 'location', 'description', 'required_skills',
                  'nice_to_have', 'experience_level', 'salary_range', 'is_active')
        widgets = {
            'title':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Senior Python Developer'}),
            'company':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'location':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Remote / New York'}),
            'description':     forms.Textarea(attrs={'class': 'form-control', 'rows': 9, 'placeholder': 'Full job description...'}),
            'required_skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, PostgreSQL, Docker'}),
            'nice_to_have':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kubernetes, GraphQL (optional)'}),
            'experience_level': forms.Select(attrs={'class': 'form-select'}),
            'salary_range':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. $80k – $110k'}),
            'is_active':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'required_skills': 'Comma-separated. Used by the NLP engine for skill matching.',
            'description':     'Detailed description. TF-IDF similarity is computed against the resume.',
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model  = Application
        fields = ('resume_file', 'cover_letter')
        widgets = {
            'resume_file':  forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf,.docx'}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Optional cover letter...'}),
        }

    def clean_resume_file(self):
        f = self.cleaned_data.get('resume_file')
        if f:
            if not (f.name.lower().endswith('.pdf') or f.name.lower().endswith('.docx')):
                raise forms.ValidationError('Only PDF and DOCX files are accepted.')
            if f.content_type not in ('application/pdf',
                                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
                raise forms.ValidationError('Invalid file type. Upload a PDF or DOCX.')
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File must be smaller than 10 MB.')
        return f


class RecruiterNotesForm(forms.ModelForm):
    class Meta:
        model  = Application
        fields = ('status', 'recruiter_notes')
        widgets = {
            'status':          forms.Select(attrs={'class': 'form-select'}),
            'recruiter_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
