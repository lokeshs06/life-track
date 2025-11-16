from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError
from .models import UserProfile, HealthLog, Goal, NutritionEntry


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'height', 'weight', 'target_weight', 'gender', 'activity_level']


class HealthLogForm(forms.ModelForm):
    class Meta:
        model = HealthLog
        # Exclude 'date' since it's set automatically in the view
        fields = ['calories_intake', 'protein', 'carbs', 'fats', 'water_intake', 
                 'steps', 'exercise_duration', 'exercise_type', 'sleep_hours', 
                 'heart_rate', 'blood_pressure_sys', 'blood_pressure_dia', 'mood', 'notes']
        widgets = {
            'exercise_type': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'e.g., Running, Cycling, Yoga'
            }),
            'calories_intake': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0',
                'placeholder': 'Enter calories consumed today'
            }),
            'protein': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0', 'step': '0.1',
                'placeholder': 'Protein intake in grams'
            }),
            'carbs': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0', 'step': '0.1',
                'placeholder': 'Carbs intake in grams'
            }),
            'fats': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0', 'step': '0.1',
                'placeholder': 'Fats intake in grams'
            }),
            'water_intake': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0', 'step': '0.1',
                'placeholder': 'Water consumed in liters'
            }),
            'steps': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0',
                'placeholder': 'Number of steps walked'
            }),
            'exercise_duration': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0',
                'placeholder': 'Exercise duration in minutes'
            }),
            'sleep_hours': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '0', 'max': '24', 'step': '0.5',
                'placeholder': 'Hours of sleep (0-24)'
            }),
            'heart_rate': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '30', 'max': '220',
                'placeholder': 'Heart rate (30-220 bpm)'
            }),
            'blood_pressure_sys': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '50', 'max': '300',
                'placeholder': 'Systolic pressure (50-300)'
            }),
            'blood_pressure_dia': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'min': '30', 'max': '200',
                'placeholder': 'Diastolic pressure (30-200)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 resize-y bg-white',
                'rows': '5',
                'placeholder': 'Add any notes about your health, mood, or activities today...',
                'style': 'min-height: 120px;'
            }),
            'mood': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
        }


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['goal_type', 'target_value', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['age', 'height', 'weight', 'target_weight', 'gender', 'activity_level']


class NutritionEntryForm(forms.ModelForm):
    class Meta:
        model = NutritionEntry
        fields = ['meal_type', 'calories', 'water', 'protein', 'carbs', 'fat', 'fiber', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes about this meal...'}),
        }


class CustomUserCreationForm(forms.Form):
    """Custom user creation form with email field"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition',
            'placeholder': 'Choose a username'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition',
            'placeholder': 'Enter your email address'
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition',
            'placeholder': 'Create a strong password'
        })
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition',
            'placeholder': 'Re-enter your password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with that email address already exists.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2

    def save(self):
        """Create and return a new user with the form data"""
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1']
        )
        return user


class CustomPasswordResetForm(forms.Form):
    """Custom password reset form that accepts both email and username"""
    email_or_username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none rounded-lg relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition',
            'placeholder': 'Enter your email or username'
        })
    )

    def clean_email_or_username(self):
        email_or_username = self.cleaned_data['email_or_username']
        
        # Try to find user by email or username
        try:
            user = User.objects.get(email__iexact=email_or_username)
            return email_or_username
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=email_or_username)
                # Check if user has an email for password reset
                if not user.email:
                    raise ValidationError(
                        "This user account doesn't have an email address associated with it. "
                        "Please contact support for password reset assistance."
                    )
                return email_or_username
            except User.DoesNotExist:
                raise ValidationError("No user found with this email or username.")

    def get_users(self, email_or_username):
        """Return matching user(s) who should receive a reset email."""
        # First try to find by email
        try:
            user = User.objects.get(email__iexact=email_or_username)
            if user.is_active and user.email:
                yield user
        except User.DoesNotExist:
            # Then try by username
            try:
                user = User.objects.get(username__iexact=email_or_username)
                if user.is_active and user.email:
                    yield user
            except User.DoesNotExist:
                pass

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=None,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the user.
        """
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.sites.shortcuts import get_current_site
        from django.core.mail import EmailMultiAlternatives
        from django.template import loader
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        email_or_username = self.cleaned_data["email_or_username"]
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        
        if token_generator is None:
            token_generator = default_token_generator

        for user in self.get_users(email_or_username):
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                **(extra_email_context or {}),
            }
            subject = loader.render_to_string(subject_template_name, context)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            body = loader.render_to_string(email_template_name, context)

            email_message = EmailMultiAlternatives(subject, body, from_email, [user.email])
            if html_email_template_name is not None:
                html_email = loader.render_to_string(html_email_template_name, context)
                email_message.attach_alternative(html_email, 'text/html')

            email_message.send()