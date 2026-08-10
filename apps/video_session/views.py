from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VideoSessionForm
from .models import VideoSession
from .utils import create_zoom_meeting, get_zoom_meeting_details


@login_required
def video_session_list(request):
    is_officer = getattr(request.user, "is_officer", False)
    cache_key = f"video_sessions_list_{'officer' if is_officer else 'borrower'}_{request.user.id}"
    sessions = cache.get(cache_key)

    if sessions is None:
        if is_officer:
            sessions = (
                VideoSession.objects.filter(loan_officer=request.user)
                .select_related("loan", "borrower", "loan_officer")
                .order_by("-schedule_date", "-schedule_time")
            )
        else:
            sessions = (
                VideoSession.objects.filter(borrower=request.user)
                .select_related("loan", "borrower", "loan_officer")
                .order_by("-schedule_date", "-schedule_time")
            )

        sessions = list(sessions)

        # Sync live Zoom info or ensure fields are populated
        for session in sessions:
            if session.zoom_meeting_id and not session.meeting_url:
                zoom_info = get_zoom_meeting_details(session.zoom_meeting_id)
                if zoom_info:
                    session.meeting_url = zoom_info.get("join_url")
                    session.save(update_fields=["meeting_url"])

        cache.set(cache_key, sessions, timeout=300)

    base_template = (
        "loan_officer_app/loan_officer_base.html"
        if is_officer
        else "borrower_app/borrower_base.html"
    )

    context = {
        "title": "Video Sessions",
        "sessions": sessions,
        "base_template": base_template,
    }

    return render(request, "video_session/video_session_list.html", context)


@login_required
def video_session_create(request):
    is_officer = getattr(request.user, "is_officer", False)

    if not is_officer:
        messages.error(request, "You do not have permission to schedule video sessions.")
        return redirect("video_session:video_session_list")

    if request.method == "POST":
        form = VideoSessionForm(request.POST, user=request.user)

        if form.is_valid():
            session = form.save(commit=False)

            # loan_officer is set automatically by the form (disabled field
            # forced to request.user), so no manual assignment needed here
            session.save()

            if session.schedule_date and session.schedule_time:
                start_time_str = (
                    f"{session.schedule_date.isoformat()}T"
                    f"{session.schedule_time.isoformat()}Z"
                )

                topic = (
                    f"Loan Consultation - #{session.loan.id if session.loan else 'General'}"
                )

                duration = session.duration_minutes or 30

                zoom_data = create_zoom_meeting(
                    topic=topic,
                    start_time=start_time_str,
                    duration_minutes=duration,
                )

                if zoom_data:
                    session.zoom_meeting_id = str(zoom_data.get("meeting_id"))
                    session.meeting_url = zoom_data.get("join_url")
                    if hasattr(session, "start_url"):
                        session.start_url = zoom_data.get("start_url")
                    session.save()

                    messages.success(
                        request,
                        "Video session scheduled and Zoom meeting created successfully!",
                    )
                else:
                    messages.warning(
                        request,
                        "Session saved, but failed to generate Zoom meeting automatically.",
                    )

            # Cache Invalidation
            if session.borrower:
                cache.delete(f"video_sessions_list_borrower_{session.borrower.id}")

            if session.loan_officer:
                cache.delete(f"video_sessions_list_officer_{session.loan_officer.id}")

            return redirect("video_session:video_session_list")

    else:
        form = VideoSessionForm(user=request.user)

    context = {
        "title": "Schedule Video Session",
        "form": form,
    }

    return render(request, "video_session/video_session_form.html", context)


@login_required
def video_session_update(request, pk):
    is_officer = getattr(request.user, "is_officer", False)

    if not is_officer:
        messages.error(request, "You do not have permission to update video sessions.")
        return redirect("video_session:video_session_list")

    session = get_object_or_404(VideoSession, pk=pk)

    if session.loan_officer != request.user:
        messages.error(
            request,
            "You do not have permission to edit this video session.",
        )
        return redirect("video_session:video_session_list")

    if request.method == "POST":
        form = VideoSessionForm(request.POST, instance=session, user=request.user)

        if form.is_valid():
            updated_session = form.save()

            # Cache Invalidation
            if updated_session.borrower:
                cache.delete(f"video_sessions_list_borrower_{updated_session.borrower.id}")

            if updated_session.loan_officer:
                cache.delete(f"video_sessions_list_officer_{updated_session.loan_officer.id}")

            cache.delete(f"video_session_detail_{session.pk}")

            messages.success(request, "Video session details updated successfully!")

            return redirect("video_session:video_session_list")

    else:
        form = VideoSessionForm(instance=session, user=request.user)

    context = {
        "title": "Edit Video Session",
        "form": form,
        "session": session,
    }

    return render(request, "video_session/video_session_form.html", context)


@login_required
def video_session_delete(request, pk):
    is_officer = getattr(request.user, "is_officer", False)

    if not is_officer:
        messages.error(request, "You do not have permission to delete video sessions.")
        return redirect("video_session:video_session_list")

    session = get_object_or_404(VideoSession, pk=pk)

    if session.loan_officer != request.user:
        messages.error(
            request,
            "You do not have permission to delete this video session.",
        )
        return redirect("video_session:video_session_list")

    if request.method == "POST":
        borrower_id = session.borrower.id if session.borrower else None
        officer_id = session.loan_officer.id if session.loan_officer else None

        session.delete()

        # Cache Invalidation
        if borrower_id:
            cache.delete(f"video_sessions_list_borrower_{borrower_id}")

        if officer_id:
            cache.delete(f"video_sessions_list_officer_{officer_id}")

        cache.delete(f"video_session_detail_{pk}")

        messages.success(request, "Video session has been deleted successfully.")

        return redirect("video_session:video_session_list")

    context = {
        "title": "Delete Video Session",
        "session": session,
    }

    return render(
        request,
        "video_session/video_session_confirm_delete.html",
        context,
    )