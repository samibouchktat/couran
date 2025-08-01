# inventory/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

ROLE_PROTECTED_PATHS = {
    'admin': [
        '/admin/', '/dashboard/admin', '/payments/', '/classrooms/', '/teachers/',
        '/children/admin/', '/progress/'
    ],
    'teacher': [
        '/dashboard/teacher', '/children/', '/presence/', '/progress/'
    ]
}

class RoleBasedAccessMiddleware:
    """
    Middleware pour bloquer l'accès aux pages en fonction du rôle.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated:
            current_path = request.path
            if user.role == 'admin':
                # Empêche les admins d'accéder aux vues professeurs si nécessaire
                if any(current_path.startswith(path) for path in ROLE_PROTECTED_PATHS.get('teacher', [])):
                    return redirect('inventory:admin_dashboard')
            elif user.role == 'teacher':
                # Empêche les professeurs d’accéder aux vues admin
                if any(current_path.startswith(path) for path in ROLE_PROTECTED_PATHS.get('admin', [])):
                    return redirect('inventory:teacher_dashboard')

        return self.get_response(request)


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            public_urls = [
                reverse('inventory:login'),
                reverse('inventory:home'),
            ]
            if request.path not in public_urls and not request.path.startswith('/admin/'):
                return redirect('inventory:login')
        return self.get_response(request)
