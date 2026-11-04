from django import forms
from .models import Question, Category

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_text', 'description', 'category', 
            'poll_type', 'visibility', 'status', 
            'start_date', 'end_date'
        ]
        widgets = {
            'question_text': forms.TextInput(attrs={'placeholder': 'Enter poll title / question'}),
            'description': forms.Textarea(attrs={'placeholder': 'Enter description...', 'rows': 3}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'placeholder': 'Category description...', 'rows': 2}),
        }


from django.contrib.auth import get_user_model
User = get_user_model()

class AdminUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}), required=False, help_text="Leave blank to keep existing password")

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'exampleadmin@gmail.com'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email.endswith('admin@gmail.com') or email == 'superadmin@gmail.com':
            raise forms.ValidationError("Admin email address must end with 'admin@gmail.com'.")
        
        # Check if email is already in use
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
            
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
