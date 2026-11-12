from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ModerationReport
from .serializers import ModerationReportSerializer, ModerationActionSerializer, QuestionModerationSerializer
from .permissions import IsModeratorOrAdmin
from discussions.models import Report
from questions.models import Question
from questions.serializers import QuestionSerializer
from notifications.models import Notification
from notifications.services import notify

class ModerationReportListView(APIView):

    permission_classes = [IsModeratorOrAdmin]
    def get(self, request):
        reports = Report.objects.filter(status=Report.Status.PENDING)
        
        for report in reports:
            ModerationReport.objects.get_or_create(report=report)
            
        moderation_reports = ModerationReport.objects.filter(report__status=Report.Status.PENDING)
        serializer = ModerationReportSerializer(moderation_reports, many=True)
        
        return Response(serializer.data)
    

class ModerationReportDetailView(APIView):

    permission_classes = [IsModeratorOrAdmin]
    
    def dismiss(self, moderation_report, moderator):
        report = moderation_report.report

        report.status = Report.Status.DISMISSED
        report.reviewed_by = moderator
        report.resolved_at = timezone.now()
        report.save()

        moderation_report.action = ModerationReport.Action.DISMISS
        moderation_report.moderator = moderator
        moderation_report.reviewed_at = timezone.now()
        moderation_report.save()
    
    def edit(self, moderation_report, moderator, data):

        report = moderation_report.report

        if report.question:
            question = report.question
            
            if "title" in data:
                question.title = data["title"]
            if "description" in data:
                question.description = data["description"]

            question.save()
            notify_moderated(question.author, moderator, "question", question.id)

        elif report.solution:
            solution = report.solution

            if "content" in data:
                solution.content = data["content"]

            solution.save()
            notify_moderated(solution.author, moderator, "solution", solution.id)

        elif report.comment:
            comment = report.comment

            if "content" in data:
                comment.content = data["content"]

            comment.save()
            notify_moderated(comment.author, moderator, "comment", comment.id)

        report.status = Report.Status.ACTIONED
        report.reviewed_by = moderator
        report.resolved_at = timezone.now()
        report.save()

        moderation_report.action = ModerationReport.Action.EDIT
        moderation_report.moderator = moderator
        moderation_report.reviewed_at = timezone.now()
        moderation_report.save()
    
    def remove(self, moderation_report, moderator):
        report = moderation_report.report

        if report.question:
            question = report.question
            question.status = Question.QuestionStatus.REMOVED
            question.save(update_fields=["status"])
            notify_moderated(question.author, moderator, "question", question.id)
        elif report.solution:
            solution = report.solution
            author = solution.author
            solution_id = solution.id
            solution.delete()
            notify_moderated(author, moderator, "solution", solution_id)
        elif report.comment:
            comment = report.comment
            author = comment.author
            comment_id = comment.id
            comment.delete()
            notify_moderated(author, moderator, "comment", comment_id)

        report.status = Report.Status.ACTIONED
        report.reviewed_by = moderator
        report.resolved_at = timezone.now()
        report.save()

        moderation_report.action = ModerationReport.Action.REMOVE
        moderation_report.moderator = moderator
        moderation_report.reviewed_at = timezone.now()
        moderation_report.save()

    def get(self, request, id):
        moderation_report = get_object_or_404(ModerationReport, id=id, report__status=Report.Status.PENDING)
        serializer = ModerationReportSerializer(moderation_report)
        return Response(serializer.data)

    def patch(self, request, id):
        moderation_report = get_object_or_404(ModerationReport, id=id, report__status=Report.Status.PENDING)
        serializer = ModerationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == ModerationReport.Action.DISMISS:
            self.dismiss(moderation_report, request.user)
        elif action == ModerationReport.Action.EDIT:
            self.edit(moderation_report, request.user, serializer.validated_data)
        elif action == ModerationReport.Action.REMOVE:
            self.remove(moderation_report, request.user)

        moderation_report.refresh_from_db()
        response_serializer = ModerationReportSerializer(moderation_report)
        return Response(response_serializer.data)
    
class PendingQuestionListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):

        questions = Question.objects.filter(status=Question.QuestionStatus.PENDING_REVIEW, is_deleted=False)
        serializer = QuestionSerializer(questions, many=True)
        
        return Response(serializer.data)

class QuestionModerationDetailView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def patch(self, request, id):

        question = get_object_or_404(Question, id=id, status=Question.QuestionStatus.PENDING_REVIEW, is_deleted=False)

        serializer = QuestionModerationSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]

        if action == "publish":
            question.status = Question.QuestionStatus.PUBLISHED

        elif action == "remove":
            question.status = Question.QuestionStatus.REMOVED

        question.save(update_fields=["status"])
        notify_moderated(question.author, request.user, "question", question.id)

        return Response(QuestionSerializer(question).data, status=status.HTTP_200_OK)


def notify_moderated(author, moderator, reference_type, reference_id):
    if author is None or author.id == moderator.id:
        return
    notify(author, Notification.NotificationType.CONTENT_MODERATED, reference_type, reference_id)