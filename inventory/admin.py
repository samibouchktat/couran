# inventory/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, School, Parent, Teacher, Classroom, Child, Progress, Payment, Presence
# inventory/forms.py
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
# Dynamically register all models except those with composite primary keys


admin.site.register(School) 
admin.site.register(Parent)
admin.site.register(Teacher)
admin.site.register(Classroom)
admin.site.register(Child)
admin.site.register(Progress)
admin.site.register(Payment)
admin.site.register(Presence)
@admin.register(CustomUser)
class CustomUserAdmin(DjangoUserAdmin):
    add_form  = CustomUserCreationForm
    form      = CustomUserChangeForm
    model     = CustomUser

    list_display  = ('username', 'email', 'role', 'is_active')
    list_filter   = ('role', 'is_active')
    search_fields = ('username', 'email')
    ordering      = ('username',)

    fieldsets = (
        (None,            {'fields': ('username', 'email', 'password')}),
        ('Rôle & profil', {'fields': ('role', 'school')}),
        ('Permissions',   {'fields': ('is_active','is_superuser','groups','user_permissions')}),
        ('Dates',         {'fields': ('last_login','date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username','email','role','school','password1','password2'),
        }),
    )