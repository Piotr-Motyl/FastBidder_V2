from django.urls import path
from . import views

urlpatterns = [
    path("compare/", views.compare_files, name="compare_files"),
]
