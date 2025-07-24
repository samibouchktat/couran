from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.conf import settings



class School(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        db_table = 'school'


class CustomUser(AbstractUser):
    id = models.BigAutoField(
        db_column='user_id',
        primary_key=True,
        editable=False,
        verbose_name='ID'
    )
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('teacher', 'Professeur'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    school = models.ForeignKey(
        School, on_delete=models.SET_NULL, blank=True, null=True
    )
    # On remplace les M2M hérités pour pointer sur users_* plutôt qu’auth_*
    groups = models.ManyToManyField(
        Group, related_name='customuser_set', blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission, related_name='customuser_permissions', blank=True
    )

    def __str__(self):
        return self.username or f"Utilisateur #{self.pk}"

    class Meta:
        db_table = 'users'


class Parent(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='id'
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    num_children = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'parents'


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='id'
    )
    experience_years = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'teachers'


class Classroom(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, blank=True, null=True
    )
    max_children = models.IntegerField(
        blank=True, null=True, db_column='number_max_children'
    )
    date_created = models.CharField(
        max_length=255, blank=True, null=True, db_column='date_create'
    )
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        db_table = 'classrooms'


class Child(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='id'
    )
    parent = models.ForeignKey(
        Parent, on_delete=models.SET_NULL, blank=True, null=True, db_column='parents_id'
    )
    classroom = models.ForeignKey(
        Classroom, on_delete=models.SET_NULL,
        blank=True, null=True, related_name='children'
    )
    arabic_level = models.CharField(max_length=255, blank=True, null=True)
    learning_level = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'children'


class Progress(models.Model):
    id = models.BigAutoField(primary_key=True)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, blank=True, null=True)
    surah = models.CharField(max_length=255, blank=True, null=True)
    verse = models.CharField(max_length=255, blank=True, null=True)
    hizb = models.CharField(max_length=255, blank=True, null=True)
    chapter = models.IntegerField(blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)
    performance = models.CharField(max_length=255, blank=True, null=True)
    date_retention = models.DateField(blank=True, null=True)
    validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='validated_progress'
    )
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        db_table = 'progress'


class Payment(models.Model):
    PENDING = 'pending'
    PAID    = 'paid'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (PAID,    'Payé'),
    ]
    id = models.BigAutoField(primary_key=True)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.FloatField()
    date_payment = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        blank=False,
        null=False,
        help_text="Statut du paiement"
    )
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        db_table = 'payments'


class Presence(models.Model):
    id = models.BigAutoField(primary_key=True)
    child = models.ForeignKey(Child, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    present = models.BooleanField(default=True)

    class Meta:
        db_table = 'presence'
        unique_together = ('child', 'date')
