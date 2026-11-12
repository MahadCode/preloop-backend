from django.urls import path
from .views import (
    CompanyDetailView,
    CompanyView,
    JobRoleDetailView,
    JobRoleView,
    TagDetailView,
    TagView,
)

urlpatterns = [
    path("companies/", CompanyView.as_view(), name="company-list-create"),
    path("companies/<int:id>/", CompanyDetailView.as_view(), name="company-detail"),
    path("job-roles/", JobRoleView.as_view(), name="jobrole-list-create"),
    path("job-roles/<int:id>/", JobRoleDetailView.as_view(), name="jobrole-detail"),
    path("tags/", TagView.as_view(), name="tag-list-create"),
    path("tags/<int:id>/", TagDetailView.as_view(), name="tag-detail"),
]