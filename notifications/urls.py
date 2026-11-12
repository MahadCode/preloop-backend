from django.urls import path
from .views import MarkAllNotificationsReadView, NotificationDetailView, NotificationListView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("read-all/", MarkAllNotificationsReadView.as_view(), name="notification-read-all"),
    path("<int:id>/", NotificationDetailView.as_view(), name="notification-detail"),
]
