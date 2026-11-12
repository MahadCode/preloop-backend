from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from .serializers import SolutionSerializer, CommentSerializer, ReportSerializer, QuestionCommentSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Solution, Comment, Report
from questions.models import Question
from accounts.permissions import IsVerifiedUser
from notifications.models import Notification
from notifications.services import notify


class SolutionCreateView(APIView):
    permission_classes = [IsVerifiedUser]
    
    def get(self, request, id):
        question = get_object_or_404(Question, id=id)
        solutions = Solution.objects.filter(question=question)
        if solutions:
            serializer = SolutionSerializer(solutions, many=True)
            return Response(serializer.data)
        return Response({"message": "No Solutions Found"}, status=status.HTTP_404_NOT_FOUND)
        
    def post(self, request, id):
        serializer = SolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = get_object_or_404(Question, id=id)
        solution = serializer.save(author=request.user, question=question)
        if question.author_id and question.author_id != request.user.id:
            notify(
                question.author,
                Notification.NotificationType.NEW_SOLUTION,
                "solution",
                solution.id,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SolutionDetailView(APIView):
    permission_classes = [IsVerifiedUser]
    
    def get(self, request, id):
        solution = get_object_or_404(Solution, id=id)

        serializer = SolutionSerializer(solution)
        return Response(serializer.data)

    def patch(self, request, id):
        solution = get_object_or_404(Solution, id=id)

        if request.user.id == solution.author.id:
            serializer = SolutionSerializer(solution, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(status=status.HTTP_403_FORBIDDEN)

    def delete(self, request, id):
        solution = get_object_or_404(Solution, id=id)

        if request.user.id == solution.author.id:
            solution.delete()
            return Response({"message": "Solution Deletion Successful"})

        return Response(status=status.HTTP_403_FORBIDDEN)


class CommentCreateView(APIView):
    permission_classes = [IsVerifiedUser]

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=request.user)
        recipient = comment_recipient(comment, request.user.id)
        if recipient is not None:
            notify(recipient, Notification.NotificationType.NEW_REPLY, "comment", comment.id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    permission_classes = [IsVerifiedUser]
    
    def get(self, request):
        comments = Comment.objects.all()
        if comments.exists():
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        return Response( {"message": "No comments found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, id):
        comment = get_object_or_404(Comment, id=id)

        if request.user.id == comment.author.id:
            serializer = CommentSerializer(comment, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(status=status.HTTP_403_FORBIDDEN)

    def delete(self, request, id):
        comment = get_object_or_404(Comment, id=id)

        if request.user.id == comment.author.id:
            comment.delete()
            return Response({"message": "Comment Deletion Successful"})

        return Response(status=status.HTTP_403_FORBIDDEN)


class ReportListCreateView(APIView):
    permission_classes = [IsVerifiedUser]
    
    def get(self, request):
        reports = Report.objects.filter(reporter=request.user)
        
        if reports.exists():
            serializer = ReportSerializer(reports, many=True)
            return Response(serializer.data)

        return Response( {"message": "No reports found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(reporter=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ReportDetailView(APIView):
    permission_classes = [IsVerifiedUser]

    def get_object(self, id, user):
        return get_object_or_404(Report, id=id, reporter=user)

    def get(self, request, id):
        report = self.get_object(id, request.user)
        serializer = ReportSerializer(report)
        return Response(serializer.data)

    def patch(self, request, id):
        report = self.get_object(id, request.user)
        serializer = ReportSerializer(report, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        report = self.get_object(id, request.user)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class QuestionCommentListView(APIView):
    permission_classes = [IsVerifiedUser]
    
    def get(self, request, id):
        question = get_object_or_404(Question, id=id, is_deleted=False)
        comments = Comment.objects.filter(question=question)
        serializer = QuestionCommentSerializer(comments, many=True)
        return Response(serializer.data)


class SolutionCommentListView(APIView):
    permission_classes = [IsVerifiedUser]

    def get(self, request, id):
        solution = get_object_or_404(Solution, id=id)
        comments = Comment.objects.filter(solution=solution)
        serializer = QuestionCommentSerializer(comments, many=True)
        return Response(serializer.data)


def comment_recipient(comment, actor_id):
    if comment.reply_to_id and comment.reply_to.author_id and comment.reply_to.author_id != actor_id:
        return comment.reply_to.author
    if comment.question_id and comment.question.author_id and comment.question.author_id != actor_id:
        return comment.question.author
    if comment.solution_id and comment.solution.author_id and comment.solution.author_id != actor_id:
        return comment.solution.author
    return None
        
