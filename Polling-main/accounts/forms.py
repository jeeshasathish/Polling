from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "yourname@gmail.com"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        
        # Block users from registering as ADMIN or SUPER_ADMIN
        if email == "superadmin@gmail.com" or email.endswith("admin@gmail.com"):
            raise forms.ValidationError("You cannot register an administrator account.")
            
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
            
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get("email").strip().lower()
        user.email = email
        user.username = email  # Set username to email for Django compatibility
        if commit:
            user.save()
        return user
