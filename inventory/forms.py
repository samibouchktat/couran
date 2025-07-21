# inventory/forms.py

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import CustomUser

class CustomUserCreationForm(forms.ModelForm):
    """
    Formulaire pour créer un nouvel utilisateur (admin ou prof).
    """
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmation', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'school')

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if not p1 or not p2 or p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(forms.ModelForm):
    """
    Formulaire pour mettre à jour un utilisateur existant.
    Affiche le mot de passe sous forme masquée.
    """
    password = ReadOnlyPasswordHashField(label="Mot de passe")

    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'password',
            'role', 'school',
            'is_active', 'is_superuser',
            'groups', 'user_permissions'
        )