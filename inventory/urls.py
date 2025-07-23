# inventory/urls.py
from django.urls import path
from . import views
from django.contrib.auth import logout  
from django.shortcuts import redirect 
app_name = 'inventory'

urlpatterns = [

    # Authentification
    path('', views.home, name='home'),

    path('login/', views.custom_login, name='login'),
    path('logout/', lambda r: (logout(r), redirect('inventory:login'))[1], name='logout'),
    # Dashboards
    path('dashboard/admin/',   views.admin_dashboard,   name='admin_dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),

    # CRUD Professeurs
    path('teachers/', views.TeacherListView.as_view(), name='teacher-list'),
    path('teachers/add/', views.TeacherCreateView.as_view(), name='teacher-add'),
    path('teachers/<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher-edit'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher-delete'),

    # CRUD Groupes
    path('classrooms/', views.ClassroomListView.as_view(), name='classroom-list'),
    path('classrooms/add/', views.ClassroomCreateView.as_view(), name='classroom-add'),
    path('classrooms/<int:pk>/edit/', views.ClassroomUpdateView.as_view(), name='classroom-edit'),
    path('classrooms/<int:pk>/delete/', views.ClassroomDeleteView.as_view(), name='classroom-delete'),
    path('classrooms/<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom-detail'),

    # CRUD Enfants
    path('children/', views.ChildListView.as_view(), name='child-list'),
    path('children/add/', views.ChildCreateView.as_view(), name='child-add'),
    path('children/<int:pk>/edit/', views.ChildUpdateView.as_view(), name='child-edit'),
    path('children/<int:pk>/delete/', views.ChildDeleteView.as_view(), name='child-delete'),

    # CRUD Progression
    path('progress/', views.ProgressListView.as_view(), name='progress-list'),
    path('progress/add/', views.ProgressCreateView.as_view(), name='progress-add'),
    path('progress/<int:pk>/edit/', views.ProgressUpdateView.as_view(), name='progress-edit'),

    # CRUD Paiements
    path(
        'payments/export/',
        views.payment_export,
        name='payment-export'
    ),

    # Par exemple, vos CRUD Payment :
    path('payments/export/', views.payment_export, name='payment-export'),
    path('presence/export/<int:year>/<int:month>/', views.export_presence_month, name='presence-export'),
    path('payments/',         views.PaymentListView.as_view(),   name='payment-list'),
    path('payments/add/',     views.PaymentCreateView.as_view(), name='payment-add'),
    path('payments/<int:pk>/edit/',   views.PaymentUpdateView.as_view(), name='payment-edit'),
    path('payments/<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment-delete'),
    # Présences
        path(
        'presence/export/<int:year>/<int:month>/',
        views.export_presence_month,
        name='presence-export'
    ),
    path('presence/', views.PresenceListView.as_view(), name='presence-list'),
    path('presence/add/', views.PresenceCreateView.as_view(), name='presence-add'),
    path('presence/export/<int:year>/<int:month>/', views.export_presence_month, name='presence-export'),
]