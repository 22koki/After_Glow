import mimetypes

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Memory, Universe
from .serializers import (
    MemoryCreateSerializer, MemorySerializer, RegisterSerializer, UniverseSerializer,
)

User = get_user_model()


def is_owner(request, universe):
    return bool(request.user.is_authenticated and universe.owner_id == request.user.pk)


def can_access(request, universe):
    return is_owner(request, universe) or universe.accepts_invite(
        request.headers.get("X-Universe-Invite", "")
    )


def accessible_universe(request, pk):
    universe = get_object_or_404(Universe, pk=pk)
    if not can_access(request, universe):
        # Hide whether a private universe exists.
        raise NotFound("Universe not found or invitation invalid.")
    return universe


def auth_data(user, token):
    return {
        "token": token.key,
        "user": {"name": user.first_name or user.username, "email": user.email},
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    email = values["email"].strip().lower()
    if User.objects.filter(username__iexact=email).exists():
        raise ValidationError({"email": "An account with this email already exists."})
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, first_name=values["name"],
                password=values["password"],
            )
            token = Token.objects.create(user=user)
    except IntegrityError:
        raise ValidationError({"email": "An account with this email already exists."})
    return Response(auth_data(user, token), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))
    user = authenticate(username=email, password=password)
    if not user or not user.is_active:
        raise PermissionDenied("Invalid email or password.")
    token, _ = Token.objects.get_or_create(user=user)
    return Response(auth_data(user, token))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({"name": request.user.first_name or request.user.username, "email": request.user.email})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def universes(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Sign in to create and manage universes.")
    if request.method == "GET":
        return Response(UniverseSerializer(Universe.objects.filter(owner=request.user), many=True).data)
    serializer = UniverseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    universe = serializer.save(owner=request.user)
    invite = universe.issue_invite()
    return Response({
        "universe": UniverseSerializer(universe).data,
        "invite_token": invite,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def universe_detail(request, pk):
    universe = accessible_universe(request, pk)
    return Response({
        **UniverseSerializer(universe).data,
        "is_owner": is_owner(request, universe),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rotate_invite(request, pk):
    universe = get_object_or_404(Universe, pk=pk, owner=request.user)
    token = universe.issue_invite()
    return Response({"invite_token": token})


@api_view(["GET", "POST"])
def memories(request, pk):
    universe = accessible_universe(request, pk)
    owner = is_owner(request, universe)
    if request.method == "GET":
        items = universe.memories.all()
        if not owner:
            items = items.filter(approved=True)
        return Response(MemorySerializer(items, many=True).data)

    if not owner and not universe.allow_guest_posts:
        raise PermissionDenied("Guest contributions are closed for this universe.")
    serializer = MemoryCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    item = serializer.save(
        universe=universe,
        submitted_by=request.user if request.user.is_authenticated else None,
        approved=owner,
    )
    return Response(MemorySerializer(item).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def moderate_memory(request, pk):
    item = get_object_or_404(Memory.objects.select_related("universe"), pk=pk)
    if not is_owner(request, item.universe):
        raise PermissionDenied("Only the creator can approve memories.")
    action = request.data.get("action")
    if action == "approve":
        item.approved = True
        item.save(update_fields=["approved"])
        return Response(MemorySerializer(item).data)
    if action == "reject":
        attachment = item.attachment
        item.delete()
        if attachment:
            attachment.delete(save=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
    raise ValidationError({"action": "Use approve or reject."})


@api_view(["GET"])
def memory_media(request, pk):
    item = get_object_or_404(Memory.objects.select_related("universe"), pk=pk)
    if not can_access(request, item.universe):
        raise NotFound("Attachment unavailable.")
    if not is_owner(request, item.universe) and not item.approved:
        raise NotFound("Attachment unavailable.")
    from django.utils import timezone
    if item.unlock_at and item.unlock_at > timezone.now():
        raise NotFound("This memory is still sealed.")
    if not item.attachment:
        raise NotFound("This memory has no attachment.")
    content_type = mimetypes.guess_type(item.attachment.name)[0] or "application/octet-stream"
    response = FileResponse(item.attachment.open("rb"), content_type=content_type, as_attachment=False)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
