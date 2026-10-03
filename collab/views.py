import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import WorkItem, WorkItemEvent, Meeting, MeetingParticipant, MeetingMessage
from .services import run_scan, workload_summary


def _office(user):
    return getattr(user, "is_office", False) or user.is_staff or user.is_superuser


# ---------- AI Work queue ----------
@login_required
def worklist(request):
    if not _office(request.user):
        return redirect("dashboard:home")
    items = list(WorkItem.objects.filter(status="OPEN").order_by("-priority", "due_at", "-created_at")[:300])
    groups = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for it in items:
        groups[it.priority].append(it)
    labels = dict(WorkItem.CATEGORY)
    cat_counts = []
    for code, label in WorkItem.CATEGORY:
        n = sum(1 for it in items if it.category == code)
        if n:
            cat_counts.append({"code": code, "label": label, "n": n})
    return render(request, "collab/worklist.html", {
        "summary": workload_summary(items), "groups": groups, "count": len(items),
        "cat_counts": cat_counts})


@login_required
@require_POST
def work_action(request, pk, verb):
    if not _office(request.user):
        return redirect("dashboard:home")
    it = get_object_or_404(WorkItem, pk=pk)
    note = (request.POST.get("note") or "").strip()
    if verb == "resolve":
        it.status = "RESOLVED"; it.resolved_by = request.user; it.resolved_at = timezone.now(); it.decision_note = note
    elif verb == "dismiss":
        it.status = "DISMISSED"; it.resolved_by = request.user; it.resolved_at = timezone.now(); it.decision_note = note
    elif verb == "snooze":
        it.status = "SNOOZED"; it.snooze_until = timezone.now() + timezone.timedelta(days=int(request.POST.get("days", 3)))
    it.save()
    WorkItemEvent.objects.create(item=it, actor=request.user, action=verb, note=note)
    return redirect("collab:worklist")


@login_required
@require_POST
def work_scan(request):
    if not _office(request.user):
        return redirect("dashboard:home")
    r = run_scan()
    messages.success(request, f"Analyse IA terminee — {r['created']} nouveaux, {r['auto_closed']} clotures.")
    return redirect("collab:worklist")


# ---------- Meetings ----------
@login_required
def meetings(request):
    if not _office(request.user):
        return redirect("dashboard:home")
    from accounts.models import User, Role
    mine = Meeting.objects.filter(requested_by=request.user)
    invited = Meeting.objects.filter(participants=request.user)
    upcoming = (mine | invited).distinct().exclude(status__in=["DECLINED", "CANCELLED", "DONE"]).order_by("proposed_at")
    past = (mine | invited).distinct().filter(status__in=["DONE", "CANCELLED", "DECLINED"]).order_by("-proposed_at")[:20]
    my_responses = {mp.meeting_id: mp.response for mp in MeetingParticipant.objects.filter(user=request.user)}
    office_users = User.objects.exclude(role=Role.CAREGIVER).exclude(pk=request.user.pk).order_by("role", "first_name")
    prefill_client = None
    _cid = request.GET.get("client")
    if _cid:
        from clients.models import Client
        prefill_client = Client.objects.filter(pk=_cid).first()
    return render(request, "collab/meetings.html", {
        "upcoming": upcoming, "past": past, "office_users": office_users,
        "my_responses": my_responses, "prefill_client": prefill_client})


@login_required
@require_POST
def meeting_request(request):
    if not _office(request.user):
        return redirect("dashboard:home")
    from accounts.models import User
    title = (request.POST.get("title") or "").strip()
    when = request.POST.get("proposed_at")
    if not title or not when:
        messages.error(request, "Titre et date/heure requis.")
        return redirect("collab:meetings")
    try:
        dt = timezone.datetime.fromisoformat(when)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
    except (ValueError, TypeError):
        messages.error(request, "Date/heure invalide.")
        return redirect("collab:meetings")
    _cid = request.POST.get("client") or None
    m = Meeting.objects.create(
        title=title, purpose=(request.POST.get("purpose") or "").strip(),
        requested_by=request.user, proposed_at=dt,
        duration_min=int(request.POST.get("duration_min", 30) or 30),
        location=(request.POST.get("location") or "").strip(),
        client_id=_cid if _cid else None)
    ids = request.POST.getlist("participants")
    for u in User.objects.filter(pk__in=ids):
        MeetingParticipant.objects.get_or_create(meeting=m, user=u)
    # notify participants if the notifications app is available
    try:
        from notifications.services import notify
        for u in User.objects.filter(pk__in=ids):
            notify(u, f"Reunion demandee : {title}", level="INFO")
    except Exception:
        pass
    messages.success(request, "Reunion creee. Salle prete : chat + audio/video. Les participants sont notifies.")
    return redirect("collab:meeting_room", pk=m.id)


@login_required
@require_POST
def meeting_respond(request, pk, answer):
    m = get_object_or_404(Meeting, pk=pk)
    mp = get_object_or_404(MeetingParticipant, meeting=m, user=request.user)
    mp.response = "ACCEPTED" if answer == "accept" else "DECLINED"
    mp.responded_at = timezone.now(); mp.save()
    # confirm the meeting once anyone accepts
    if answer == "accept" and m.status == "REQUESTED":
        m.status = "CONFIRMED"; m.save(update_fields=["status"])
    return redirect("collab:meetings")


def _can_access_meeting(user, m):
    return (_office(user) or m.requested_by_id == user.id
            or m.responses.filter(user=user).exists())


@login_required
def meeting_room(request, pk):
    """Teams-style meeting room: in-app text chat + one-click video call (Jitsi)."""
    m = get_object_or_404(Meeting, pk=pk)
    if not _can_access_meeting(request.user, m):
        return redirect("dashboard:home")
    return render(request, "collab/meeting_room.html", {
        "m": m, "participants": m.responses.select_related("user")})


@login_required
@require_POST
def meeting_post(request, pk):
    m = get_object_or_404(Meeting, pk=pk)
    if not _can_access_meeting(request.user, m):
        return JsonResponse({"detail": "Accès refusé."}, status=403)
    text = (json.loads(request.body or "{}").get("text") or "").strip()
    if not text:
        return JsonResponse({"detail": "Message vide."}, status=400)
    msg = MeetingMessage.objects.create(meeting=m, user=request.user, text=text[:2000])
    return JsonResponse({"id": msg.id, "user": request.user.get_full_name() or request.user.username,
                         "me": True, "text": msg.text, "at": timezone.localtime(msg.at).strftime("%H:%M")})


@login_required
def meeting_messages(request, pk):
    m = get_object_or_404(Meeting, pk=pk)
    if not _can_access_meeting(request.user, m):
        return JsonResponse({"messages": []}, status=403)
    after = request.GET.get("after")
    qs = m.messages.select_related("user")
    if after and after.isdigit():
        qs = qs.filter(id__gt=int(after))
    out = [{"id": x.id,
            "user": (x.user.get_full_name() or x.user.username) if x.user else "Système",
            "me": x.user_id == request.user.id,
            "text": x.text, "at": timezone.localtime(x.at).strftime("%H:%M")} for x in qs[:200]]
    return JsonResponse({"messages": out})


@login_required
@require_POST
def meeting_update(request, pk, action):
    m = get_object_or_404(Meeting, pk=pk)
    if m.requested_by_id != request.user.id and not request.user.is_staff:
        return redirect("collab:meetings")
    m.status = {"cancel": "CANCELLED", "done": "DONE"}.get(action, m.status)
    m.save(update_fields=["status"])
    return redirect("collab:meetings")
