from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Company, JobRole, Tag
from .serializers import CompanySerializer, JobRoleSerializer, TagSerializer

def save_named_entry(model, serializer_class, request):
    raw = request.data.get("name", "")
    name = raw.strip() if isinstance(raw, str) else ""
    if not name:
        return Response({"name": ["Enter a name."]}, status=status.HTTP_400_BAD_REQUEST)

    existing = model.objects.filter(name__iexact=name).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.save(update_fields=["is_active"])
        return Response(serializer_class(existing).data)

    serializer = serializer_class(data={"name": name})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        companies = Company.objects.filter(is_active=True)
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)

    def post(self, request):
        return save_named_entry(Company, CompanySerializer, request)
        
        

class JobRoleView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        job_roles = JobRole.objects.filter(is_active=True)
        serializer = JobRoleSerializer(job_roles, many=True)
        return Response(serializer.data)

    def post(self, request):
        return save_named_entry(JobRole, JobRoleSerializer, request)


class TagView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        tags = Tag.objects.filter(is_active=True)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request):
        return save_named_entry(Tag, TagSerializer, request)


class TaxonomyDetailView(APIView):
    permission_classes = [IsAuthenticated]
    model = None
    serializer_class = None

    def patch(self, request, id):
        entry = get_object_or_404(self.model, id=id)
        serializer = self.serializer_class(entry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, id):
        entry = get_object_or_404(self.model, id=id)
        entry.is_active = False
        entry.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyDetailView(TaxonomyDetailView):
    model = Company
    serializer_class = CompanySerializer


class JobRoleDetailView(TaxonomyDetailView):
    model = JobRole
    serializer_class = JobRoleSerializer


class TagDetailView(TaxonomyDetailView):
    model = Tag
    serializer_class = TagSerializer