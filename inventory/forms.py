# inventory/forms.py

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import CustomUser
from .models import Presence,Progress, Child
from django import forms
from .models import  Classroom, Parent
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
    PERFORMANCE_CHOICES = [
        ('ضعيف', 'ضعيف'),
        ('متوسط', 'متوسط'),
        ('جيد', 'جيد'),
        ('جيد جدًا', 'جيد جدًا'),
        ('ممتاز', 'ممتاز'),
    ]


    performance = forms.ChoiceField(
        choices=PERFORMANCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='تقييم'
    )

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
            'comment':         forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # on **ne** met **pas** 'performance' ici : on l’a déjà déclaré plus haut
            'date_retention':  forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'validated':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'surah':          'سورة',
            'verse':          'آيات',
            'hizb':           'حزب',
            'chapter':        'فصل',
            'note':           'ملاحظة',
            'comment':        'تعليق',
            'date_retention': 'تاريخ المراجعة',
            'validated':      'اعتماد التقدم',
        }


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['user', 'classroom', 'parent', 'arabic_level', 'learning_level']

    def __init__(self, *args, **kwargs):
        # On récupère la requête pour filtrer les classes
        request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # Afficher le nom complet ou le username pour les users
        self.fields['user'].label_from_instance = (
            lambda obj: obj.get_full_name() or obj.username
        )

        # Optionnel : ne proposer que les CustomUser dont role == 'child'
        # self.fields['user'].queryset = CustomUser.objects.filter(role='child')

        # Limiter les salles au prof connecté
        if request_user and request_user.role == 'teacher':
            self.fields['classroom'].queryset = Classroom.objects.filter(
                teacher__user=request_user
            )
# inventory/forms.py



class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['user', 'classroom', 'parent', 'arabic_level', 'learning_level']

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

        # === Élève  ===
        # afficher nom complet ou username
        self.fields['user'].label_from_instance = (
            lambda u: u.get_full_name() or u.username
        )
        # si vous voulez limiter aux « enfants » :
        # self.fields['user'].queryset = CustomUser.objects.filter(role='child')

        # === Salle de classe ===
        # n’afficher que les classes du prof connecté
        if request_user and request_user.role == 'teacher':
            self.fields['classroom'].queryset = Classroom.objects.filter(
                teacher__user=request_user
            )
        # afficher le nom de la salle
        self.fields['classroom'].label_from_instance = lambda cls: cls.name or f"Salle #{cls.pk}"

        # === Parent ===
        # si vous voulez limiter aux parents existants
        self.fields['parent'].queryset = Parent.objects.all()
        # afficher le nom du parent (via son user lié)
        self.fields['parent'].label_from_instance = (
            lambda p: p.user.get_full_name() or p.user.username
        )
class BulkAssignChildrenForm(forms.Form):
    children = forms.ModelMultipleChoiceField(
        queryset=Child.objects.select_related('user').all(),
        widget=forms.CheckboxSelectMultiple,
        label="Enfants à affecter"
    )
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.select_related('teacher__user').all(),
        label="Classe (professeur associé)"
    )   