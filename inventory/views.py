#invventory/views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404



from .models import CustomUser, Child

# Décorateurs personnalisés
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect('home')        # ou la page d’accueil de votre choix
        else:
            messages.error(request, "Identifiants invalides")
    return render(request, 'login.html')
def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Accès réservé à l'administrateur.".encode('utf-8'), content_type='text/plain')
    return _wrapped_view

def teacher_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role == 'professeur':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Accès réservé aux professeurs.".encode('utf-8'), content_type='text/plain')
    return _wrapped_view

# Vue de login personnalisée
def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, 'role'):
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'professeur':
                    return redirect('teacher_dashboard')
                else:
                    logout(request)
                    messages.error(request, "Rôle utilisateur inconnu.")
            else:
                logout(request)
                messages.error(request, "Aucun rôle défini pour cet utilisateur.")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    return render(request, 'login.html')

# Vue dashboard admin
@admin_required
def admin_dashboard(request):
    # À compléter avec les stats et liens admin
    return render(request, 'dashboard_admin.html')

# Vue dashboard professeur
@teacher_required
def teacher_dashboard(request):
    # À compléter avec les stats et liens prof
    return render(request, 'dashboard_teacher.html')


def home(request):
    return render(request, 'inventory/home.html')

# ---------- TEACHER CRUD (Admin only) ----------
class TeacherListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    template_name = 'inventory/teacher_list.html'
    context_object_name = 'teachers'

    def test_func(self):
        return self.request.user.role == 'admin'

    def get_queryset(self):
        return CustomUser.objects.filter(role='teacher')

class TeacherCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CustomUser
    template_name = 'inventory/teacher_form.html'
    fields = ['username','first_name','last_name','email','role']
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password('changeme')  # default password, prompt to reset
        user.role = 'teacher'
        user.save()
        return super().form_valid(form)

class TeacherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    template_name = 'inventory/teacher_form.html'
    fields = ['first_name','last_name','email']
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class TeacherDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomUser
    template_name = 'inventory/teacher_confirm_delete.html'
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

# ---------- CHILD CRUD (Teacher) ----------
class ChildListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Child
    template_name = 'inventory/child_list.html'
    context_object_name = 'children'

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_queryset(self):
        return Child.objects.filter(child_class__teacher=self.request.user)

class ChildCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Child
    template_name = 'inventory/child_form.html'
    fields = ['id','child_class','parents','arabic_level','learning_level']
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

class ChildUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Child
    template_name = 'inventory/child_form.html'
    fields = ['child_class','parents','arabic_level','learning_level']
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

class ChildDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Child
    template_name = 'inventory/child_confirm_delete.html'
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'
