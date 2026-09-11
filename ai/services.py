"""
Panther AI Care Coordinator — rule-based operational intelligence.

Design rule from the brief: the AI *recommends and prioritises*. It never makes
sensitive clinical decisions autonomously and never diagnoses a patient. Its risk
output is always "potential concern — professional review recommended".

Everything here is plain functions over the ORM — no heavy abstraction — so it's
easy to later swap a rule for an ML model without touching the callers.
"""
from math import radians, sin, cos, asin, sqrt

from django.utils import timezone

from caregivers.models import Caregiver
from scheduling.models import Visit, VisitStatus


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km. Returns None if any coordinate is missing."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 1)


def _weekly_hours(caregiver, ref):
    """Approx. scheduled hours this week — used to avoid overloading a caregiver."""
    week_start = ref - timezone.timedelta(days=ref.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = 0
    qs = caregiver.visits.filter(scheduled_start__gte=week_start,
                                 scheduled_start__lt=week_start + timezone.timedelta(days=7))
    for v in qs:
        seconds += (v.scheduled_end - v.scheduled_start).total_seconds()
    return seconds / 3600


def _has_conflict(caregiver, start, end, exclude_visit_id=None):
    qs = caregiver.visits.filter(scheduled_start__lt=end, scheduled_end__gt=start).exclude(
        status__in=[VisitStatus.CANCELLED, VisitStatus.MISSED])
    if exclude_visit_id:
        qs = qs.exclude(id=exclude_visit_id)
    return qs.exists()


def _continuity(caregiver, client):
    """How many completed visits this caregiver has had with this client."""
    return Visit.objects.filter(caregiver=caregiver, client=client,
                                status=VisitStatus.COMPLETED).count()


def _arrival(caregiver, visit):
    """Estimate whether the caregiver can realistically arrive on time, based on
    their previous visit that day (travel time vs the gap before this visit)."""
    prev = (Visit.objects.filter(caregiver=caregiver,
                                 scheduled_end__lte=visit.scheduled_start,
                                 scheduled_start__date=timezone.localtime(visit.scheduled_start).date())
            .select_related("client").order_by("-scheduled_end").first())
    if not prev:
        return {"has_prev": False, "confidence": 95}
    km = haversine_km(prev.client.latitude, prev.client.longitude,
                      visit.client.latitude, visit.client.longitude)
    travel_min = round((km or 3) / 28 * 60)  # ~28 km/h urban
    gap_min = round((visit.scheduled_start - prev.scheduled_end).total_seconds() / 60)
    if gap_min >= travel_min + 10:
        conf = 95
    elif gap_min >= travel_min:
        conf = 82
    else:
        conf = 60
    return {"has_prev": True, "prev_end": timezone.localtime(prev.scheduled_end).strftime("%H:%M"),
            "travel_min": travel_min, "gap_min": gap_min, "confidence": conf}


def match_caregivers(visit, top_n=3):
    """
    Panther CareMatch — score available caregivers for a visit and return the best,
    with a component breakdown, a continuity signal, a plain-language explanation,
    a recommendation tier, and arrival confidence. The coordinator stays in control.
    """
    from incidents.models import Incident
    client = visit.client
    required = set()
    if hasattr(client, "care_plan"):
        required = set(client.care_plan.required_skills.values_list("id", flat=True))
    pref_lang = (client.preferred_language or "").strip().lower()

    results = []
    for cg in Caregiver.objects.filter(active=True).prefetch_related("skills"):
        if _has_conflict(cg, visit.scheduled_start, visit.scheduled_end, visit.id):
            continue
        cg_skills = set(cg.skills.values_list("id", flat=True))
        skill_fit = 1.0 if not required else len(required & cg_skills) / len(required)
        if required and skill_fit == 0:
            continue

        distance = haversine_km(client.latitude, client.longitude,
                                cg.home_latitude, cg.home_longitude)
        dist_score = 0.6 if distance is None else max(0.0, 1 - min(distance, 25) / 25)
        lang_ok = (not pref_lang or pref_lang in [l.lower() for l in cg.language_list()])
        lang_score = 1.0 if lang_ok else 0.7
        hours = _weekly_hours(cg, visit.scheduled_start)
        load_score = 1.0 if hours < cg.weekly_hours_cap * 0.8 else (
            0.6 if hours < cg.weekly_hours_cap else 0.2)
        rel_score = cg.reliability_score / 100
        punc_score = cg.punctuality_score / 100
        cont_count = _continuity(cg, client)
        cont_score = min(cont_count / 6.0, 1.0)

        score = (0.28 * skill_fit + 0.17 * dist_score + 0.15 * rel_score
                 + 0.10 * punc_score + 0.15 * cont_score + 0.05 * lang_score
                 + 0.10 * load_score)
        pct = round(score * 100)

        # Display dimensions (raw 0–100 sub-scores, the "CareMatch breakdown")
        dimensions = [
            ("Expérience / compétences", round(skill_fit * 100)),
            ("Proximité", round(dist_score * 100)),
            ("Fiabilité", cg.reliability_score),
            ("Ponctualité", cg.punctuality_score),
            ("Continuité avec le client", round(cont_score * 100)),
            ("Communication / langue", round(lang_score * 100)),
        ]
        # Plain-language explanation
        bits = []
        if cont_count:
            bits.append(f"a déjà accompagné {client.first_name} {cont_count} fois")
        else:
            bits.append("n'a pas encore accompagné ce client")
        bits.append(f"ponctualité {cg.punctuality_score}%")
        if not Incident.objects.filter(client=client, caregiver=cg).exists():
            bits.append("aucun incident signalé")
        if pref_lang and lang_ok:
            bits.append(f"parle {client.preferred_language.lower()}")
        if distance is not None:
            bits.append(f"à {round(distance)} km")
        why = f"{cg.full_name} " + ", ".join(bits) + "."

        tier = "recommended" if pct >= 85 else ("alternative" if pct >= 65 else "not_recommended")

        results.append({
            "caregiver": cg, "score": pct,
            "components": {  # kept for the existing explainability bar
                "skills": round(0.28 * skill_fit * 100), "distance": round(0.17 * dist_score * 100),
                "reliability": round(0.15 * rel_score * 100), "punctuality": round(0.10 * punc_score * 100),
                "workload": round(0.10 * load_score * 100), "language": round(0.05 * lang_score * 100),
            },
            "dimensions": dimensions, "why": why, "tier": tier,
            "continuity_count": cont_count,
            "distance_km": distance, "skill_fit": round(skill_fit * 100),
            "reliability": cg.reliability_score, "weekly_hours": round(hours, 1),
            "workload": "Normale" if load_score >= 0.9 else ("Élevée" if load_score < 0.6 else "Modérée"),
            "skills_ok": bool(not required or skill_fit == 1.0),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    top = results[:top_n]
    for r in top:
        r["arrival"] = _arrival(r["caregiver"], visit)
    return top


def client_continuity(client, limit=5):
    """Who knows this client best — caregivers ranked by completed-visit count."""
    from django.db.models import Count
    rows = (Visit.objects.filter(client=client, status=VisitStatus.COMPLETED,
                                 caregiver__isnull=False)
            .values("caregiver__code", "caregiver__first_name", "caregiver__last_name")
            .annotate(n=Count("id")).order_by("-n")[:limit])
    return [{"code": r["caregiver__code"],
             "name": f"{r['caregiver__first_name']} {r['caregiver__last_name']}",
             "visits": r["n"]} for r in rows]




# ---- Risk detection on care reports -------------------------------------------------

CONCERN_TERMS = [
    "étourdiss", "vertige", "chute", "tombé", "douleur", "confus", "désorient",
    "essouffl", "fièvre", "saign", "refus", "agité", "detresse", "détresse",
]


CATEGORY_LABELS = {"MEDICAL": "Médical", "CLINICAL": "Clinique",
                   "FUNCTIONAL": "Fonctionnel", "GENERAL": "Général"}
SEVERITY_LABELS = {0: "Aucune", 1: "Faible", 2: "Moyenne", 3: "Élevée"}

_HIGH_TERMS = ["chute", "saigne", "saignement", "détresse", "fièvre", "malaise",
               "perte de connaissance", "douleur intense", "vomit", "vomissement",
               "essouffl", "convuls", "inconscien"]
_MED_TERMS = ["étourdiss", "vertige", "confus", "désorient", "douleur", "agité",
              "anxi", "refus", "insomnie", "œdème", "oedème", "tension élevée"]
_LEX = {
    "MEDICAL": ["médicament", "tension", "pouls", "plaie", "infection", "pansement",
                "fièvre", "douleur", "vomit", "saigne", "œdème", "oedème", "glycémie",
                "injection", "traitement"],
    "CLINICAL": ["confus", "désorient", "mémoire", "étourdiss", "vertige", "chute",
                 "agité", "anxi", "dépress", "humeur", "hallucin", "sommeil", "insomnie"],
    "FUNCTIONAL": ["mobilit", "marche", "hygiène", "toilette", "repas", "appétit",
                   "transfert", "habill", "déplace", "autonomie", "fatigue"],
}


def classify_note(text):
    """Classify a care note → (category, severity 0-3). Guidance, not a diagnosis."""
    t = (text or "").lower()
    if not t.strip():
        return "GENERAL", 0
    if any(term in t for term in _HIGH_TERMS):
        severity = 3
    elif any(term in t for term in _MED_TERMS):
        severity = 2
    else:
        severity = 0
    scores = {cat: sum(1 for w in words if w in t) for cat, words in _LEX.items()}
    best = max(scores, key=scores.get)
    category = best if scores[best] > 0 else "GENERAL"
    if severity == 0 and category != "GENERAL":
        severity = 1
    return category, severity


def scan_report_for_risk(report):
    """
    Flag a report for human review if its notes or mood suggest a concern, and
    classify the note for Care Insights (category + severity).
    Sets ai_flagged / ai_concern / insight_* on the report.
    """
    text = (report.notes or "").lower()
    hits = [t for t in CONCERN_TERMS if t in text]
    low_mood = report.mood is not None and report.mood <= 2

    category, severity = classify_note(report.notes)
    if low_mood and severity < 2:
        severity = 2
    report.insight_category = category
    report.insight_severity = severity

    if hits or low_mood:
        reason = "humeur basse signalée" if low_mood and not hits else \
                 "signes rapportés à surveiller"
        report.ai_flagged = True
        report.ai_concern = f"Préoccupation potentielle — revue professionnelle recommandée ({reason})."
    report.save(update_fields=["ai_flagged", "ai_concern",
                               "insight_category", "insight_severity"])
    return report.ai_concern

    if report.ai_flagged:  # clear a previously-set flag if edited to be benign
        report.ai_flagged = False
        report.ai_concern = ""
        report.save(update_fields=["ai_flagged", "ai_concern"])
    return ""


# ---- Daily operations brief ---------------------------------------------------------

def daily_brief(now=None):
    """
    Build the 08:00-style operations brief the coordinator sees on the dashboard.
    Pure read-only aggregation over today's visits.
    """
    now = now or timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timezone.timedelta(days=1)
    todays = Visit.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end)

    from django.db.models import Q
    scheduled = todays.exclude(status=VisitStatus.CANCELLED)
    confirmed = scheduled.filter(status__in=[VisitStatus.IN_PROGRESS, VisitStatus.COMPLETED]).count()
    uncovered = scheduled.filter(
        Q(caregiver__isnull=True) | Q(status=VisitStatus.UNCOVERED)).distinct().count()
    late = sum(1 for v in scheduled if v.minutes_late > 0)
    total = scheduled.count()
    completed = scheduled.filter(status=VisitStatus.COMPLETED).count()
    on_schedule = round(100 * (total - uncovered - late) / total) if total else 100

    lines = [f"Opérations à {on_schedule}% sur le planning aujourd'hui."]
    actions = uncovered + late
    if actions:
        lines.append(f"{actions} action(s) de remplacement recommandée(s).")
    else:
        lines.append("Aucune action urgente recommandée.")
    summary = " ".join(lines)
    summary = _maybe_ai_summary(
        {"on_schedule": on_schedule, "total": total, "confirmed": confirmed,
         "uncovered": uncovered, "late": late, "completed": completed},
        summary)

    return {
        "on_schedule_pct": on_schedule,
        "confirmed": confirmed,
        "scheduled": total,
        "completed": completed,
        "uncovered": uncovered,
        "late": late,
        "summary": summary,
    }


def _maybe_ai_summary(context, fallback):
    """
    If an AI provider key is configured, use a natural-language brief — but NEVER block
    the page waiting for it. If the AI text isn't cached yet, we return the instant
    rule-based summary now and generate the AI version in a background thread so it's
    ready (cached) on the next load. Always safe; never raises.
    """
    try:
        from ai import llm
        if not llm.available():
            return fallback
        from django.core.cache import cache
        ckey = "ai_brief_" + timezone.localtime().strftime("%Y%m%d%H")  # refresh hourly
        cached = cache.get(ckey)
        if cached:
            return cached

        prompt = (
            "Voici l'état des opérations d'une agence de soins à domicile aujourd'hui : "
            f"{context['confirmed']}/{context['total']} visites confirmées, "
            f"{context['completed']} terminées, {context['late']} soignant(s) en retard, "
            f"{context['uncovered']} visite(s) non couverte(s), "
            f"{context['on_schedule']}% dans les temps. "
            "Rédige un résumé opérationnel en 2 phrases courtes, en français, ton "
            "professionnel et rassurant, pour le coordinateur. Pas de liste, pas de titre.")

        # Mark as in-progress so we only spawn one generator, then warm in background.
        if cache.add(ckey + "_lock", 1, 60):
            import threading

            def _warm():
                try:
                    text = llm.complete(
                        prompt,
                        system=("Tu es le coordinateur IA de Panther Home Care, une "
                                "plateforme de gestion des soins à domicile à Lubumbashi."),
                        max_tokens=200)
                    if text and text.strip():
                        cache.set(ckey, text.strip(), 3600)
                except Exception:
                    pass

            threading.Thread(target=_warm, daemon=True).start()

        return fallback  # instant — the dashboard never waits on the network
    except Exception:
        return fallback


# ---- Analytics & workforce intelligence ---------------------------------------------

def analytics_snapshot(days=14):
    """
    Aggregate operational KPIs and time-series for the Analytics dashboard.
    Read-only; returns plain dicts/lists ready to hand to Chart.js.
    """
    from django.db.models import Avg, Count
    from django.db.models.functions import TruncDate

    from clients.models import Client
    from incidents.models import Incident
    from reports.models import CareReport

    now = timezone.localtime()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timezone.timedelta(days=days - 1)

    # Day buckets
    labels, keys = [], []
    for i in range(days):
        d = (start + timezone.timedelta(days=i)).date()
        keys.append(d)
        labels.append(d.strftime("%d/%m"))

    def _by_day(qs, field="scheduled_start"):
        rows = (qs.annotate(d=TruncDate(field)).values("d")
                .annotate(n=Count("id")).order_by("d"))
        m = {r["d"]: r["n"] for r in rows}
        return [m.get(k, 0) for k in keys]

    visits = Visit.objects.filter(scheduled_start__date__gte=start.date())
    visits_total = _by_day(visits)
    visits_done = _by_day(visits.filter(status=VisitStatus.COMPLETED))

    reports = CareReport.objects.filter(created_at__date__gte=start.date())
    flags_series = _by_day(reports.filter(ai_flagged=True), field="created_at")

    # Average client mood per day (satisfaction proxy, scaled to %)
    mood_rows = (reports.annotate(d=TruncDate("created_at")).values("d")
                 .annotate(m=Avg("mood")).order_by("d"))
    mood_map = {r["d"]: r["m"] for r in mood_rows}
    mood_series = [round((mood_map.get(k, 0) or 0) * 20) for k in keys]

    # Risk distribution
    risk_rows = Client.objects.values("risk_level").annotate(n=Count("id"))
    risk_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_map = {r["risk_level"]: r["n"] for r in risk_rows}
    risk_counts = [risk_map.get(k, 0) for k in risk_order]

    # Incidents by severity
    sev_rows = Incident.objects.values("severity").annotate(n=Count("id"))
    sev_map = {r["severity"]: r["n"] for r in sev_rows}
    sev_counts = [sev_map.get(k, 0) for k in risk_order]

    # Caregiver workload — top by scheduled hours over the last 30 days
    win = today - timezone.timedelta(days=30)
    load = []
    for cg in Caregiver.objects.filter(active=True).prefetch_related("visits"):
        secs = sum((v.scheduled_end - v.scheduled_start).total_seconds()
                   for v in cg.visits.filter(scheduled_start__gte=win))
        if secs:
            load.append((cg.code, round(secs / 3600)))
    load.sort(key=lambda x: x[1], reverse=True)
    all_hours = sum(h for _, h in load)
    load = load[:8]
    occ_labels = [c for c, _ in load]
    occ_hours = [h for _, h in load]

    # KPI headline figures
    n_active = Caregiver.objects.filter(active=True).count() or 1
    # rough capacity over the window: caregivers * weekly cap * ~4.3 weeks
    capacity = n_active * 45 * (30 / 7)
    utilization = min(100, round(100 * all_hours / capacity)) if capacity else 0
    completed_30 = Visit.objects.filter(status=VisitStatus.COMPLETED,
                                        scheduled_start__gte=win).count()
    avg_mood = reports.aggregate(m=Avg("mood"))["m"] or 0
    open_incidents = Incident.objects.exclude(status="RESOLVED").count()

    return {
        "labels": labels,
        "visits_total": visits_total,
        "visits_done": visits_done,
        "flags": flags_series,
        "mood": mood_series,
        "risk_labels": ["Faible", "Moyen", "Élevé", "Critique"],
        "risk_counts": risk_counts,
        "sev_counts": sev_counts,
        "occ_labels": occ_labels,
        "occ_hours": occ_hours,
        "kpi": {
            "utilization": utilization,
            "avg_visits_day": round(sum(visits_total) / max(len(visits_total), 1), 1),
            "satisfaction": round(avg_mood * 20),
            "completed_30": completed_30,
            "open_incidents": open_incidents,
        },
    }


# ---- Caregiver self-service: open-visit match scoring --------------------------------

def caregiver_visit_score(caregiver, visit):
    """
    Score how well ONE caregiver fits ONE visit, from the caregiver's point of view.

    Blends the same signals as the coordinator matcher (skills, distance, reliability,
    punctuality, workload, language) and then adjusts for environment/preference
    attributes (pets, smoking household, gender preference). Returns the percentage
    plus human-readable reasons for any deductions — this is the "attribute score"
    caregivers see next to each open visit.
    """
    client = visit.client
    required = set()
    if hasattr(client, "care_plan"):
        required = set(client.care_plan.required_skills.values_list("id", flat=True))
    cg_skills = set(caregiver.skills.values_list("id", flat=True))
    skill_fit = 1.0 if not required else len(required & cg_skills) / len(required)

    distance = haversine_km(client.latitude, client.longitude,
                            caregiver.home_latitude, caregiver.home_longitude)
    dist_score = 0.6 if distance is None else max(0.0, 1 - min(distance, 25) / 25)

    pref_lang = (client.preferred_language or "").strip().lower()
    lang_score = 1.0 if (not pref_lang or pref_lang in
                         [l.lower() for l in caregiver.language_list()]) else 0.7
    hours = _weekly_hours(caregiver, visit.scheduled_start)
    load_score = 1.0 if hours < caregiver.weekly_hours_cap * 0.8 else (
        0.6 if hours < caregiver.weekly_hours_cap else 0.2)

    base = (0.35 * skill_fit + 0.20 * dist_score
            + 0.20 * caregiver.reliability_score / 100
            + 0.10 * caregiver.punctuality_score / 100
            + 0.10 * load_score + 0.05 * lang_score)

    reasons = []
    if required and skill_fit < 1.0:
        reasons.append("Compétences partiellement couvertes")
    if getattr(client, "has_pets", False) and not getattr(caregiver, "comfortable_with_pets", True):
        base *= 0.75
        reasons.append("Le client a des animaux")
    if getattr(client, "smoking_household", False) and not getattr(caregiver, "comfortable_with_smoking", True):
        base *= 0.72
        reasons.append("Foyer fumeur")
    pref = getattr(client, "caregiver_gender_preference", "ANY")
    if pref == "FEMALE" and caregiver.gender != "F":
        base *= 0.4
        reasons.append("Le client préfère une soignante")
    elif pref == "MALE" and caregiver.gender != "M":
        base *= 0.4
        reasons.append("Le client préfère un soignant")
    if distance is not None and distance > 20:
        reasons.append(f"Distance {round(distance)} km")

    return {
        "score": max(0, min(100, round(base * 100))),
        "reasons": reasons,
        "distance_km": distance,
        "skills_ok": bool(not required or skill_fit == 1.0),
    }


def open_visits_for(caregiver, days=45):
    """Unfilled visits over the next `days`, scored for this caregiver (best first)."""
    now = timezone.localtime()
    horizon = now + timezone.timedelta(days=days)
    qs = (Visit.objects.filter(status=VisitStatus.UNCOVERED,
                               scheduled_start__gte=now, scheduled_start__lte=horizon)
          .select_related("client").order_by("scheduled_start"))
    rows = []
    for v in qs:
        s = caregiver_visit_score(caregiver, v)
        rows.append({"visit": v, **s})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


# ============================================================================
#  CareMatch — decision-support scoring (experience, continuity, arrival…)
# ============================================================================
def _continuity_count(caregiver, client):
    return Visit.objects.filter(client=client, caregiver=caregiver,
                                status=VisitStatus.COMPLETED).count()


def _arrival(caregiver, visit):
    """Can the caregiver realistically reach this visit on time?
    Looks at their previous visit that day and estimates travel from distance."""
    client = visit.client
    day0 = visit.scheduled_start.replace(hour=0, minute=0, second=0, microsecond=0)
    prev = (Visit.objects.filter(caregiver=caregiver, scheduled_start__gte=day0,
                                 scheduled_end__lte=visit.scheduled_start)
            .exclude(id=visit.id).select_related("client").order_by("-scheduled_end").first())
    if prev:
        gap = (visit.scheduled_start - prev.scheduled_end).total_seconds() / 60
        d = haversine_km(prev.client.latitude, prev.client.longitude,
                         client.latitude, client.longitude)
        origin = f"visite {prev.client.code}"
    else:
        gap = 999
        d = haversine_km(caregiver.home_latitude, caregiver.home_longitude,
                         client.latitude, client.longitude)
        origin = "domicile"
    travel = round((d or 3) / 28 * 60) + 5  # ~28 km/h city + 5 min buffer
    slack = gap - travel
    confidence = max(30, min(99, round(95 - max(0, -slack) * 4 - (0 if slack > 15 else 8))))
    return {"feasible": slack >= 0, "travel_min": travel,
            "confidence": confidence, "origin": origin,
            "prev_end": timezone.localtime(prev.scheduled_end).strftime("%H:%M") if prev else None}


def carematch(caregiver, visit):
    """Full CareMatch analysis for one caregiver on one visit."""
    client = visit.client
    required = set()
    if hasattr(client, "care_plan"):
        required = set(client.care_plan.required_skills.values_list("id", flat=True))
    cg_skills = set(caregiver.skills.values_list("id", flat=True))
    experience = 1.0 if not required else len(required & cg_skills) / len(required)

    distance = haversine_km(client.latitude, client.longitude,
                            caregiver.home_latitude, caregiver.home_longitude)
    dist_score = 0.6 if distance is None else max(0.0, 1 - min(distance, 25) / 25)

    pref = (client.preferred_language or "").strip().lower()
    lang_ok = not pref or pref in [l.lower() for l in caregiver.language_list()]
    language = 1.0 if lang_ok else 0.6

    continuity_n = _continuity_count(caregiver, client)
    continuity = min(1.0, 0.35 + continuity_n * 0.11)  # more visits → stronger bond

    reliability = caregiver.reliability_score / 100
    punctual = caregiver.punctuality_score
    # personality: stable proxy blending rapport (continuity) + reliability
    personality = min(1.0, 0.6 + continuity * 0.25 + reliability * 0.15)

    comp = {
        "experience": round(experience * 100),
        "personality": round(personality * 100),
        "distance": round(dist_score * 100),
        "reliability": punctual,
        "continuity": round(continuity * 100),
        "language": round(language * 100),
    }
    score = round(0.24 * experience + 0.14 * personality + 0.16 * dist_score
                  + 0.16 * reliability + 0.20 * continuity + 0.10 * language, 4) * 100
    score = round(score)

    arrival = _arrival(caregiver, visit)
    verdict = ("recommended" if score >= 85 else
               ("alternative" if score >= 65 else "not"))

    # "Why" explanation
    bits = []
    if continuity_n:
        bits.append(f"a accompagné {client.first_name} {continuity_n} fois")
    else:
        bits.append(f"n'a pas encore vu {client.first_name}")
    bits.append(f"ponctualité {punctual}%")
    if distance is not None:
        bits.append(f"à {round(distance, 1)} km")
    if not lang_ok:
        bits.append("écart de langue")
    if not arrival["feasible"]:
        bits.append("trajet serré avant la visite")
    why = f"{caregiver.code} " + ", ".join(bits) + "."

    return {"caregiver": caregiver, "score": score, "components": comp,
            "continuity_visits": continuity_n, "distance_km": distance,
            "arrival": arrival, "verdict": verdict, "why": why}


def carematch_ranked(visit, top_n=5):
    from caregivers.models import Caregiver
    rows = []
    for cg in Caregiver.objects.filter(active=True).prefetch_related("skills", "certifications"):
        if _has_conflict(cg, visit.scheduled_start, visit.scheduled_end, visit.id):
            continue
        rows.append(carematch(cg, visit))
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:top_n]



# ============================================================================
#  Predictive layer — churn risk + demand forecast
# ============================================================================
def churn_risk(client):
    """Predict how likely a client is to leave (0–100) with the driving factors."""
    from datetime import timedelta
    from reports.models import CareReport
    from clients.models import Invoice
    now = timezone.localtime()
    score, factors = 0, []

    recent = client.visits.filter(status=VisitStatus.COMPLETED,
                                  scheduled_start__gte=now - timedelta(days=30)).count()
    prior = client.visits.filter(status=VisitStatus.COMPLETED,
                                 scheduled_start__gte=now - timedelta(days=60),
                                 scheduled_start__lt=now - timedelta(days=30)).count()
    if prior and recent < prior * 0.6:
        score += 30; factors.append("Baisse des visites")

    last = client.visits.order_by("-scheduled_start").first()
    if last and (now - last.scheduled_start).days > 21:
        score += 20; factors.append("Sans visite récente")

    moods = [r.mood for r in CareReport.objects.filter(visit__client=client)
             .order_by("-created_at")[:10] if r.mood]
    if moods and sum(moods) / len(moods) < 2.6:
        score += 20; factors.append("Humeur en baisse")

    open_inc = client.incidents.exclude(status="RESOLVED").count() if hasattr(client, "incidents") else 0
    if open_inc:
        score += min(20, open_inc * 10); factors.append(f"{open_inc} incident(s) ouvert(s)")

    overdue = Invoice.objects.filter(client=client).exclude(status="PAID").count()
    if overdue:
        score += min(15, overdue * 8); factors.append("Factures impayées")

    return {"client": client, "score": min(100, score), "factors": factors}


def churn_ranked(top_n=8):
    from clients.models import Client
    rows = [churn_risk(c) for c in Client.objects.filter(active=True)
            .prefetch_related("visits", "incidents")]
    rows = [r for r in rows if r["score"] > 0]
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:top_n]


def demand_forecast(days=7):
    """Predict visit demand for the next `days` and flag potential coverage gaps."""
    from datetime import timedelta
    now = timezone.localtime()
    horizon = now + timedelta(days=days)
    upcoming = Visit.objects.filter(scheduled_start__gte=now, scheduled_start__lt=horizon
                                    ).exclude(status=VisitStatus.CANCELLED)
    uncovered = upcoming.filter(status=VisitStatus.UNCOVERED).count()
    # historical daily average (last 28 days completed)
    hist = Visit.objects.filter(status=VisitStatus.COMPLETED,
                                scheduled_start__gte=now - timedelta(days=28)).count()
    daily_avg = round(hist / 28, 1)
    projected = round(daily_avg * days)
    active_cg = Caregiver.objects.filter(active=True).count()
    # capacity ≈ caregivers × ~5 visits/week prorated
    capacity = round(active_cg * 5 * days / 7)
    return {"upcoming": upcoming.count(), "uncovered": uncovered,
            "daily_avg": daily_avg, "projected": projected,
            "capacity": capacity, "gap": max(0, projected - capacity)}


# ============================================================================
#  Health scores (explainable) — client & caregiver
# ============================================================================
def client_health(client):
    """A 0–100 client health score (higher = healthier) with the factors behind it.
    Explainable: returns the signals that moved the score and a confidence."""
    from datetime import timedelta
    from reports.models import CareReport
    from clients.models import Invoice
    now = timezone.localtime()
    score = 100
    factors = []

    last = client.visits.order_by("-scheduled_start").first()
    if last and (now - last.scheduled_start).days > 21:
        score -= 18; factors.append(("Sans visite depuis plus de 3 semaines", -18))

    recent = client.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=now - timedelta(days=30)).count()
    prior = client.visits.filter(status=VisitStatus.COMPLETED,
                                 scheduled_start__gte=now - timedelta(days=60),
                                 scheduled_start__lt=now - timedelta(days=30)).count()
    if prior and recent < prior * 0.6:
        score -= 15; factors.append(("Baisse de la fréquence des visites", -15))

    moods = [r.mood for r in CareReport.objects.filter(visit__client=client).order_by("-created_at")[:10] if r.mood]
    if moods and sum(moods) / len(moods) < 2.6:
        score -= 15; factors.append(("Humeur en baisse dans les rapports", -15))

    flagged = CareReport.objects.filter(visit__client=client, ai_flagged=True,
                                        created_at__gte=now - timedelta(days=30)).count()
    if flagged:
        score -= min(18, flagged * 6); factors.append((f"{flagged} rapport(s) signalé(s) par l'IA", -min(18, flagged * 6)))

    open_inc = client.incidents.exclude(status="RESOLVED").count() if hasattr(client, "incidents") else 0
    if open_inc:
        score -= min(20, open_inc * 10); factors.append((f"{open_inc} incident(s) ouvert(s)", -min(20, open_inc * 10)))

    concerns = client.concerns.exclude(status="RESOLVED").count() if hasattr(client, "concerns") else 0
    if concerns:
        score -= min(12, concerns * 6); factors.append((f"{concerns} suivi(s) clinique(s) actif(s)", -min(12, concerns * 6)))

    overdue = Invoice.objects.filter(client=client).exclude(status="PAID").count()
    if overdue:
        score -= min(8, overdue * 4); factors.append(("Factures impayées", -min(8, overdue * 4)))

    score = max(0, min(100, score))
    band = "bon" if score >= 80 else ("moyen" if score >= 55 else "à risque")
    confidence = min(95, 60 + len(factors) * 8)
    return {"score": score, "band": band, "factors": factors, "confidence": confidence}


def caregiver_health(cg):
    """A composite 0–100 caregiver score across reliability, attendance, compliance,
    feedback, documentation and utilization — with an eligibility tier."""
    from datetime import timedelta
    from reports.models import CareReport
    now = timezone.localtime()

    reliability = cg.reliability_score
    attendance = cg.punctuality_score

    expired = cg.certifications.filter(expires_on__lt=timezone.localdate()).count()
    compliance = max(0, 100 - expired * 34)

    evals = list(cg.evaluations.all())
    feedback = round(sum(e.score for e in evals) / len(evals)) if evals else 85

    completed = cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=now - timedelta(days=30))
    ndone = completed.count()
    ndoc = CareReport.objects.filter(visit__in=completed).count()
    documentation = round(100 * ndoc / ndone) if ndone else 90

    hrs = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
              for v in cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=now - timedelta(days=7))
              if v.check_in_at and v.check_out_at)
    cap = float(cg.weekly_hours_cap or 45)
    utilization = min(100, round(100 * hrs / cap)) if cap else 0

    metrics = {"Fiabilité": reliability, "Assiduité": attendance, "Conformité": compliance,
               "Retours clients": feedback, "Documentation": documentation, "Utilisation": utilization}
    score = round(0.22 * reliability + 0.20 * attendance + 0.18 * compliance
                  + 0.18 * feedback + 0.12 * documentation + 0.10 * utilization)
    if score >= 85:
        tier = ("Soignant d'excellence", "Éligible aux affectations prioritaires.")
    elif score >= 70:
        tier = ("Soignant fiable", "Affectations standard.")
    else:
        tier = ("À accompagner", "Supervision recommandée.")
    return {"score": score, "metrics": metrics, "tier": tier[0], "tier_note": tier[1]}


# ============================================================================
#  Coordinator decision engine — event → recommended action
# ============================================================================
def coordinator_actions(limit=6):
    """Turn events into recommended actions: uncovered visits → ranked replacements
    within range, and repeated symptoms in reports → clinical review."""
    from collections import defaultdict, Counter
    from datetime import timedelta
    from accounts.models import AgencySettings
    from reports.models import CareReport
    from clients.models import Client
    cfg = AgencySettings.get()
    now = timezone.localtime()
    actions = []

    # 1. Uncovered visits (now → next 24h) with qualified caregivers nearby
    horizon = now + timedelta(hours=24)
    for v in (Visit.objects.filter(status=VisitStatus.UNCOVERED, scheduled_start__gte=now,
                                   scheduled_start__lt=horizon).select_related("client")[:8]):
        matches = carematch_ranked(v, top_n=6)
        near = [m for m in matches if m["distance_km"] is not None
                and m["distance_km"] <= cfg.max_travel_km and m["score"] >= 60]
        nearest = round(min((m["distance_km"] for m in near), default=0), 1)
        actions.append({
            "type": "replacement", "priority": 1, "visit": v, "client": v.client,
            "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
            "n_qualified": len(near), "radius": cfg.max_travel_km, "nearest": nearest,
            "top": matches[0] if matches else None,
        })

    # 2. Repeated symptoms in the week's reports → clinical review
    since = now - timedelta(days=7)
    TERMS = {"étourdiss": "étourdissements", "vertige": "vertiges", "chute": "chutes",
             "douleur": "douleurs", "confus": "confusion", "essouffl": "essoufflement",
             "fièvre": "fièvre", "agité": "agitation"}
    per_client = defaultdict(Counter)
    for r in (CareReport.objects.filter(created_at__gte=since).exclude(notes="")
              .select_related("visit__client")):
        t = (r.notes or "").lower()
        for term, label in TERMS.items():
            if term in t:
                per_client[r.visit.client_id][label] += 1
    for cid, counter in per_client.items():
        for symptom, cnt in counter.items():
            if cnt >= 2:
                cl = Client.objects.filter(id=cid).first()
                if cl:
                    actions.append({"type": "clinical", "priority": 2, "client": cl,
                                    "symptom": symptom, "count": cnt})

    actions.sort(key=lambda a: (a["priority"], -a.get("count", 0)))
    return actions[:limit]
