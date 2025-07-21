# inventory/views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
import csv
from django.db.models import Avg,F, ExpressionWrapper, DateField
from django.db.models.functions import Now
from .models import Classroom, Progress, Payment, Presence, CustomUser, Teacher, Child
from .forms import CustomUserCreationForm
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string

# ——————— Authentification unique ———————

def home(request):
    return render(request, 'inventory/home.html')

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.role == 'admin':
                return redirect('inventory:admin_dashboard')
            elif user.role == 'teacher':
                return redirect('inventory:teacher_dashboard')
            else:
                logout(request)
                messages.error(request, "Rôle non reconnu.")
        else:
            messages.error(request, "Identifiants incorrects.")
    return render(request, 'login.html')

# ——————— Décorateur de rôles ———————
def role_required(allowed_roles):
    def decorator(view_func):
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Accès non autorisé.")
        return _wrapped
    return decorator

admin_required   = role_required(['admin'])
teacher_required = role_required(['teacher'])

# ——————— Dashboards ———————
@admin_required
def admin_dashboard(request):
    teachers = CustomUser.objects.filter(role='teacher').count()
    students = Child.objects.count()
    groups = Classroom.objects.count()
    total_prog = Progress.objects.count()
    validated = Progress.objects.filter(validated=True).count()
    avg_mem = (validated / total_prog * 100) if total_prog else 0
    late_pay = Payment.objects.filter(status='pending', due_date__lt=timezone.now().date()).count()
    pres_total = Presence.objects.count()
    pres_present = Presence.objects.filter(present=True).count()
    pres_rate = (pres_present / pres_total * 100) if pres_total else 0
    return render(request, 'dashboard_admin.html', {
        'teachers': teachers,
        'students': students,
        'groups': groups,
        'avg_mem': avg_mem,
        'late_pay': late_pay,
        'pres_rate': pres_rate,
        'today': timezone.localdate(),
    })
class AdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = CustomUser
    template_name = 'inventory/admin_list.html'
    context_object_name = 'admins'

    def test_func(self):
        return self.request.user.role == 'admin'

    def get_queryset(self):
        return CustomUser.objects.filter(role='admin')


class AdminCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'inventory/admin_form.html'
    success_url = reverse_lazy('inventory:admin-list')

    def test_func(self):
        return self.request.user.role == 'admin'

@teacher_required
def teacher_dashboard(request):
    classes = Classroom.objects.filter(teacher__user=request.user)
    total_students = sum(c.children.count() for c in classes)

    # moyenne de mémorisation
    avg_mem = (
        Progress.objects
                .filter(child__classroom__in=classes, validated=True)
                .aggregate(avg=Avg('performance'))['avg']
        or 0
    )

    pending_progress = Progress.objects.filter(
        child__classroom__in=classes, validated=False
    ).order_by('-date_retention')[:10]

    # retards de paiement
    late_qs = (
        Payment.objects
               .filter(child__classroom__in=classes, due_date__lt=timezone.localdate())
               .annotate(
                   days_late=ExpressionWrapper(
                       Now() - F('due_date'),
                       output_field=DateField()
                   )
               )
    )

    today = timezone.localdate()
    todays_presences = Presence.objects.filter(
        child__classroom__in=classes, date=today, present=True
    )
    todays_count = todays_presences.count()
    today_rate = (todays_count / total_students * 100) if total_students else 0

    return render(request, "dashboard_teacher.html", {
        'classes': classes,
        'total_students': total_students,
        'avg_memorization': avg_mem,
        'pending_progress': pending_progress,
        'late_payments': late_qs,
        'late_payments_count': late_qs.count(),
        'todays_presences_count': todays_count,
        'today_presence_rate': today_rate,
        'today': today,
    })

# ——————— CRUD Professeurs (CustomUser) ———————
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
    fields = ['username', 'first_name', 'last_name', 'email', 'school']
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

def form_valid(self, form):
    user = form.save(commit=False)
    user.set_password('changeme')
    user.role = 'teacher'
    user.save()

    Teacher.objects.create(user=user)
    return super().form_valid(form)

class TeacherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    template_name = 'inventory/teacher_form.html'
    fields = ['first_name', 'last_name', 'email', 'school']
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class TeacherDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomUser
    template_name = 'inventory/teacher_confirm_delete.html'
    success_url = reverse_lazy('teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

# ——————— CRUD Groupes (Classroom) ———————
class ClassroomListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Classroom
    template_name = 'inventory/classroom_list.html'
    context_object_name = 'classrooms'

    def test_func(self):
        return self.request.user.role in ['admin', 'teacher']

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Classroom.objects.all()
        return Classroom.objects.filter(teacher__user=self.request.user)

class ClassroomCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Classroom
    template_name = 'inventory/classroom_form.html'
    fields = ['name', 'teacher', 'max_children', 'date_created']
    success_url = reverse_lazy('classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class ClassroomUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Classroom
    template_name = 'inventory/classroom_form.html'
    fields = ['name', 'teacher', 'max_children', 'date_created']
    success_url = reverse_lazy('classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class ClassroomDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Classroom
    template_name = 'inventory/classroom_confirm_delete.html'
    success_url = reverse_lazy('classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'

# ——————— CRUD Enfants (Child) ———————
class ChildListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Child
    template_name = 'inventory/child_list.html'
    context_object_name = 'children'

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_queryset(self):
        return Child.objects.filter(classroom__teacher__user=self.request.user)

class ChildCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Child
    template_name = 'inventory/child_form.html'
    fields = ['user', 'classroom', 'parent', 'arabic_level', 'learning_level']
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

class ChildUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Child
    template_name = 'inventory/child_form.html'
    fields = ['classroom', 'parent', 'arabic_level', 'learning_level']
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

class ChildDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Child
    template_name = 'child_confirm_delete.html'
    success_url = reverse_lazy('child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

# ——————— CRUD Progression (Progress) ———————
class ProgressListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Progress
    template_name = 'inventory/progress_list.html'
    context_object_name = 'progress_list'

    def test_func(self):
        return self.request.user.role in ['admin', 'teacher']

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Progress.objects.all()
        return Progress.objects.filter(child__classroom__teacher__user=self.request.user)

class ProgressCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Progress
    template_name = 'inventory/progress_form.html'
    fields = ['child', 'surah', 'verse', 'hizb', 'chapter', 'note', 'comment', 'performance', 'date_retention']
    success_url = reverse_lazy('progress-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

    def form_valid(self, form):
        prog = form.save(commit=False)
        prog.validated = False
        prog.save()
        return super().form_valid(form)

class ProgressUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Progress
    template_name = 'progress_form.html'
    fields = ['validated']
    success_url = reverse_lazy('progress-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

    def form_valid(self, form):
        prog = form.save(commit=False)
        if prog.validated:
            prog.validated_by = get_object_or_404(Teacher, user=self.request.user)
        prog.save()
        return super().form_valid(form)

# ——————— CRUD Paiements (Payment) ———————
class PaymentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Payment
    template_name = "inventory/payment_list.html"
    context_object_name = "payments"

    def test_func(self):
        return self.request.user.role == 'admin'

    def get_queryset(self):
        # 1) Base queryset
        qs = super().get_queryset().select_related('child__user', 'child__classroom')
        # 2) Restreindre au prof connecté s’il ne s’agit pas d’admin :
        #    ici role=admin, donc on laisse tout.
        # 3) Filtre de recherche
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(child__user__first_name__icontains=q) |
                Q(child__user__last_name__icontains=q)  |
                Q(child__user__username__icontains=q)
            )
        return qs.order_by('-due_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        payments = ctx['payments']
        ctx.update({
            'today': today,
            'q': self.request.GET.get('q', ''),
            'total_payments': payments.count(),
            'paid_count':    payments.filter(status='paid').count(),
            'pending_count': payments.filter(status='pending', due_date__gte=today).count(),
            'late_count':    payments.filter(status='pending', due_date__lt=today).count(),
        })
        return ctx
    def get(self, request, *args, **kwargs):
        """
        Si requête AJAX (fetch), on renvoie seulement le fragment de tableau.
        Sinon, on renvoie la page complète.
        """
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "inventory/_payment_table.html",
                context,
                request=request
            )
            return JsonResponse({"table_html": html})
        return super().get(request, *args, **kwargs)
class PaymentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Payment
    template_name = 'inventory/payment_form.html'
    fields = ['child', 'amount', 'date_payment', 'due_date', 'status']
    success_url = reverse_lazy('payment-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class PaymentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Payment
    template_name = 'inventory/payment_form.html'
    fields = ['amount', 'date_payment', 'due_date', 'status']
    success_url = reverse_lazy('payment-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class PaymentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Payment
    template_name = 'inventory/payment_confirm_delete.html'
    success_url = reverse_lazy('payment-list')

    def test_func(self):
        return self.request.user.role == 'admin'

# ——————— Présences (Presence) ———————
class PresenceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Presence
    template_name = 'inventory/presence_list.html'
    context_object_name = 'presences'

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_queryset(self):
        today = timezone.localdate()
        return Presence.objects.filter(
            date=today,
            child__classroom__teacher__user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajout de today pour le template
        context['today'] = timezone.localdate()
        return context

class PresenceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Presence
    template_name = 'presence_form.html'
    fields = ['child', 'date', 'present']
    success_url = reverse_lazy('presence-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

@teacher_required
def export_presence_month(request, year, month):
    pres = Presence.objects.filter(date__year=year, date__month=month, child__classroom__teacher__user=request.user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="presence_{year}_{month}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Élève', 'Date', 'Présent'])
    for p in pres:
        writer.writerow([p.child.user.get_full_name(), p.date, p.present])
    return response

# ——————— Export CSV des paiements ———————
@login_required
def payment_export(request):
    """
    Export CSV des paiements (UTF-8 + BOM) pour Excel.
    Si ?filter=late, n’exporte que ceux dont due_date < aujourd’hui.
    """
    # Récupérer les groupes du prof connecté
    classes = Classroom.objects.filter(teacher__user=request.user)

    qs = Payment.objects.filter(child__classroom__in=classes)
    if request.GET.get('filter') == 'late':
        qs = qs.filter(due_date__lt=timezone.localdate())

    # Préparer la réponse CSV
    filename = 'paiements'
    if request.GET.get('filter') == 'late':
        filename += '_en_retard'
    filename += '.csv'

    # Attention : on précise charset utf-8 et on ajoute un BOM
    response = HttpResponse(
        content_type='text/csv; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # On écrit le BOM UTF-8 pour Excel
    response.write('\ufeff')

    # Si vous préférez le point-virgule comme séparateur :
    writer = csv.writer(response, delimiter=';')
    # Sinon, laisser delimiter=',' pour la virgule

    # En-tête
    writer.writerow([
        'Élève', 'Montant', 'Date paiement', 'Date échéance', 'Statut'
    ])

    # Lignes
    for pay in qs.select_related('child__user'):
        eleve = pay.child.user.get_full_name() or pay.child.user.username
        writer.writerow([
            eleve,
            f"{pay.amount:.2f}",
            pay.date_payment.strftime('%d/%m/%Y') if pay.date_payment else '',
            pay.due_date.strftime('%d/%m/%Y')    if pay.due_date    else '',
            pay.status or ''
        ])

    return response