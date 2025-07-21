from django.urls import path
from . import views
from .views import (
    TeacherListView, TeacherCreateView, TeacherUpdateView, TeacherDeleteView,
    ChildListView, ChildCreateView, ChildUpdateView, ChildDeleteView,
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
        # routes d’authentification
    # ========== Authentification ==========
    path('login/', views.login_view, name='login'),
    #path('logout/', views.logout_view, name='logout'),
     # Professeurs
    path('teachers/',                TeacherListView.as_view(),   name='teacher-list'),
    path('teachers/add/',            TeacherCreateView.as_view(), name='teacher-add'),
    path('teachers/<int:pk>/edit/',  TeacherUpdateView.as_view(), name='teacher-edit'),
    path('teachers/<int:pk>/delete/',TeacherDeleteView.as_view(), name='teacher-delete'),

    # Élèves
    path('children/',                ChildListView.as_view(),     name='child-list'),
    path('children/add/',            ChildCreateView.as_view(),   name='child-add'),
    path('children/<int:pk>/edit/',  ChildUpdateView.as_view(),   name='child-edit'),
    path('children/<int:pk>/delete/',ChildDeleteView.as_view(),   name='child-delete'),
]


