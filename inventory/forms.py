from django import forms
from .models import Teacher, Child

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['user', 'experience_years']

class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['user', 'parent', 'classroom', 'arabic_level', 'learning_level']
