# inventory/forms.py

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import CustomUser
from .models import Presence,Progress, Child

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


class PresenceForm(forms.ModelForm):
    class Meta:
        model = Presence
        fields = ['child', 'date', 'present']
        widgets = {
            'child':   forms.Select(attrs={'class': 'form-select'}),
            'date':    forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'present': forms.RadioSelect(choices=[(True, 'Oui'), (False, 'Non')]),
        }
class ProgressForm(forms.ModelForm):
    class Meta:
        model = Progress
        fields = [
            'child', 'surah', 'verse', 'hizb',
            'chapter', 'note', 'comment',
            'performance', 'date_retention', 'validated'
        ]
        widgets = {
            'child':           forms.Select(attrs={'class': 'form-select'}),
            'surah':           forms.TextInput(attrs={'class': 'form-control'}),
            'verse':           forms.TextInput(attrs={'class': 'form-control'}),
            'hizb':            forms.TextInput(attrs={'class': 'form-control'}),
            'chapter':         forms.NumberInput(attrs={'class': 'form-control'}),
            'note':            forms.TextInput(attrs={'class': 'form-control'}),
            'comment':         forms.Textarea(attrs={'class': 'form-control', 'rows':3}),
            'performance':     forms.NumberInput(attrs={'class': 'form-control', 'min':1, 'max':5}),
            'date_retention':  forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'validated':       forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }