from django.contrib import admin
from django.apps import apps

# Dynamically register all models except those with composite primary keys
app = apps.get_app_config('inventory')
EXCLUDE_MODELS = {'EduUsersRoles', 'NotificationData'}

for model in app.get_models():
    if model.__name__ in EXCLUDE_MODELS:
        continue
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
