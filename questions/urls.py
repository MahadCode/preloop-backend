from django.urls import path
from .views import (
    CompanyWiseQuestionView,
    MyQuestionListView,
    QuestionCreateView,
    QuestionDetailView,
    QuestionStatusBulkView,
    QuestionStatusDetailView,
    UserQuestionStatusListView,
)

urlpatterns = [
    path("", QuestionCreateView.as_view(), name="post-question"),
    path("mine/", MyQuestionListView.as_view(), name="my-questions"),
    path("statuses/", QuestionStatusBulkView.as_view(), name="question-statuses"),
    path("<int:id>/", QuestionDetailView.as_view(), name="manage-question"),
    path("company/<int:company_id>/", CompanyWiseQuestionView.as_view(), name="company-questions"),
    path("<int:id>/status/", QuestionStatusDetailView.as_view(), name="manage-question-progress-status"),
    path("progress/", UserQuestionStatusListView.as_view(), name="user-question-progress")
]
