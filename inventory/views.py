# inventory/views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.utils import timezone
import csv
from django.db.models import Avg,F, ExpressionWrapper, DateField
from django.db.models.functions import Now
from .models import Classroom, Progress, Payment, Presence, CustomUser, Teacher, Child
from .forms import CustomUserCreationForm ,PresenceForm,ProgressForm,BulkAssignChildrenForm,ChildForm
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views import View
from .constants import SURAH_LIST 
from django.contrib.auth.mixins import LoginRequiredMixin

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
     success_url = reverse_lazy('inventory:teacher-list')

     def test_func(self):
         return self.request.user.role == 'admin'

     def form_valid(self, form):
         # 1) on crée l’utilisateur
         user = form.save(commit=False)
         user.set_password('changeme')
         user.role = 'teacher'
         user.save()
         # 2) on crée le profil métier Teacher
         Teacher.objects.create(user=user)
         return super().form_valid(form)


class TeacherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CustomUser
    template_name = 'inventory/teacher_form.html'
    fields = ['first_name', 'last_name', 'email', 'school']
    success_url = reverse_lazy('inventory:teacher-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class TeacherDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CustomUser
    template_name = 'inventory/teacher_confirm_delete.html'
    success_url = reverse_lazy('inventory:teacher-list')

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
    success_url = reverse_lazy('inventory:classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class ClassroomUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Classroom
    template_name = 'inventory/classroom_form.html'
    fields = ['name', 'teacher', 'max_children', 'date_created']
    success_url = reverse_lazy('inventory:classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class ClassroomDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Classroom
    template_name = 'inventory/classroom_confirm_delete.html'
    success_url = reverse_lazy('inventory:classroom-list')

    def test_func(self):
        return self.request.user.role == 'admin'
class ClassroomDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Classroom
    template_name = 'inventory/classroom_detail.html'
    context_object_name = 'classroom'

    def test_func(self):
        # seuls l’admin et le prof assigné peuvent voir sa classe
        user = self.request.user
        if user.role == 'admin':
            return True
        # pour le prof : on vérifie que c’est bien le sien
        return self.get_object().teacher.user == user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cls = self.object
        today = timezone.localdate()

        # liste des enfants
        ctx['children'] = Child.objects.filter(classroom=cls)

        # présences du jour pour cette classe
        ctx['todays_presences'] = Presence.objects.filter(
            child__classroom=cls,
            date=today
        ).select_related('child__user')

        # 10 derniers progrès (validés ou non) pour cette classe
        ctx['recent_progress'] = Progress.objects.filter(
            child__classroom=cls
        ).order_by('-date_retention')[:10]

        ctx['today'] = today
        return ctx

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
    form_class = ChildForm
    template_name = 'inventory/child_form.html'
    success_url = reverse_lazy('inventory:child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

class ChildUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Child
    form_class = ChildForm
    template_name = 'inventory/child_form.html'
    success_url = reverse_lazy('inventory:child-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

class ChildDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Child
    template_name = 'inventory/child_confirm_delete.html'
    success_url = reverse_lazy('inventory:child-list')

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
    model         = Progress
    form_class    = ProgressForm
    template_name = 'inventory/progress_form.html'
    success_url   = reverse_lazy('inventory:progress-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['child'].queryset = Child.objects.filter(
            classroom__teacher__user=self.request.user
        )
        form.initial.setdefault('date_retention', timezone.localdate())
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['surah_list'] = SURAH_LIST
        return ctx

    def form_valid(self, form):
        form.instance.validated = False
        return super().form_valid(form)


class ProgressUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model         = Progress
    form_class    = ProgressForm
    template_name = 'inventory/progress_form.html'
    success_url   = reverse_lazy('inventory:progress-list')

    def test_func(self):
        return self.request.user.role in ['teacher', 'admin']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['child'].queryset = Child.objects.filter(
            classroom__teacher__user=self.request.user
        )
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['surah_list'] = SURAH_LIST
        return ctx

    def form_valid(self, form):
        prog = form.save(commit=False)
        if prog.validated and not prog.validated_by:
            prog.validated_by = Teacher.objects.get(user=self.request.user)
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
    success_url = reverse_lazy('inventory:payment-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class PaymentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Payment
    template_name = 'inventory/payment_form.html'
    fields = ['amount', 'date_payment', 'due_date', 'status']
    success_url = reverse_lazy('inventory:payment-list')

    def test_func(self):
        return self.request.user.role == 'admin'

class PaymentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Payment
    template_name = 'inventory/payment_confirm_delete.html'
    success_url = reverse_lazy('inventory:payment-list')

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
        return (Presence.objects
                .filter(date=today,
                        child__classroom__teacher__user=self.request.user)
                .select_related('child__user'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['today'] = timezone.localdate()
        return ctx


class PresenceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Presence
    form_class = PresenceForm
    template_name = 'inventory/presence_form.html'
    success_url = reverse_lazy('inventory:presence-list')

    def test_func(self):
        return self.request.user.role == 'teacher'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Ne proposer que les enfants de ce prof
        form.fields['child'].queryset = Child.objects.filter(
            classroom__teacher__user=self.request.user
        )
        return form

    def form_valid(self, form):
        # Si vous voulez forcer la date à aujourd'hui par défaut :
        if not form.cleaned_data.get('date'):
            form.instance.date = timezone.localdate()
        return super().form_valid(form)

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
    Export CSV des paiements, filtrés si ?filter=late.
    Fonctionne pour les professeurs OU les admins.
    """
    user = request.user

    if hasattr(user, 'teacher'):  # si c’est un professeur
        classes = Classroom.objects.filter(teacher__user=user)
        qs = Payment.objects.filter(child__classroom__in=classes)
    else:  # si c’est un admin
        qs = Payment.objects.all()

    if request.GET.get('filter') == 'late':
        qs = qs.filter(due_date__lt=timezone.localdate())

    filename = 'paiements'
    if request.GET.get('filter') == 'late':
        filename += '_en_retard'
    filename += '.csv'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Élève', 'Montant', 'Date paiement', 'Date échéance', 'Statut'])

    for pay in qs.select_related('child__user'):
        eleve = pay.child.user.get_full_name() if pay.child and pay.child.user else '---'
        writer.writerow([
            eleve,
            f"{pay.amount:.2f}",
            pay.date_payment.strftime('%d/%m/%Y') if pay.date_payment else '',
            pay.due_date.strftime('%d/%m/%Y') if pay.due_date else 'Non définie',
            dict(Payment.STATUS_CHOICES).get(pay.status, '❓')
        ])

    return response


class ChildAdminListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Liste tous les enfants, avec un bouton d’affectation pour l’admin.
    """
    model = Child
    template_name = 'inventory/child_admin_list.html'
    context_object_name = 'children'

    def test_func(self):
        return self.request.user.role == 'admin'


class ChildAssignClassView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Édite uniquement le champ 'classroom' d’un enfant pour l’admin.
    """
    model = Child
    fields = ['classroom']
    template_name = 'inventory/child_assign_class.html'
    success_url = reverse_lazy('inventory:child-admin-list')

    def test_func(self):
        return self.request.user.role == 'admin'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # On propose toutes les salles, ou on peut filtrer si besoin
        form.fields['classroom'].queryset = Classroom.objects.all().select_related('teacher__user')
        form.fields['classroom'].label = "Classe (professeur associé)"
        return form
    
class BulkAssignChildrenView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Vue pour l’affectation en bloc d’enfants à une classe.      
    """
    template_name = 'inventory/bulk_assign_children.html'

    def test_func(self):
        return self.request.user.role == 'admin'

    def get(self, request):
        form = BulkAssignChildrenForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = BulkAssignChildrenForm(request.POST)
        if form.is_valid():
            cls = form.cleaned_data['classroom']
            children = form.cleaned_data['children']
            # Affectation en bloc
            children.update(classroom=cls)
            messages.success(
                request,
                f"{children.count()} enfant(s) affecté(s) à la classe « {cls.name} »."
            )
            return redirect('inventory:bulk-assign-children')
        return render(request, self.template_name, {'form': form})
from django import template
register = template.Library()

@register.filter
def add_class(field, css):
    return field.as_widget(attrs={'class': css})
   