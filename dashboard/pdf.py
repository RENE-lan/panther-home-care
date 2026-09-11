"""Server-side PDF generation for Panther Home Care.

Pure-Python (fpdf2) so it installs with a plain `pip` on any OS — no native
libraries, no headless browser. Three documents are produced:

    client_dossier_pdf(client)      -> bytes   # the Client 360 care dossier
    care_report_pdf(report)         -> bytes   # a single post-visit report
    daily_brief_pdf(context)        -> bytes   # the coordinator operations brief

Core Helvetica is latin-1 only, so every visible string passes through _s(),
which folds smart punctuation down to latin-1. French accents survive intact.
"""
from datetime import date

from django.utils import timezone
from fpdf import FPDF

from ai.services import daily_brief
from caregivers.models import Certification
from incidents.models import Incident, IncidentStatus
from reports.models import CareReport, Mood
from scheduling.models import Visit, VisitStatus

# --- palette (mirrors the web design system) ---------------------------------
NAVY = (14, 28, 56)
ORANGE = (232, 98, 42)
GREEN = (31, 138, 76)
RED = (217, 58, 58)
AMBER = (229, 154, 28)
BLUE = (43, 108, 176)
INK = (26, 34, 51)
MUTED = (107, 118, 136)
LINE = (223, 228, 236)
SOFT = (247, 249, 252)

RISK_RGB = {"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED, "CRITICAL": (176, 30, 30)}
RISK_FR = {"LOW": "Faible", "MEDIUM": "Moyen", "HIGH": "Eleve", "CRITICAL": "Critique"}
STATUS_FR = {
    "SCHEDULED": "Planifiee", "CONFIRMED": "Confirmee", "IN_PROGRESS": "En cours",
    "COMPLETED": "Terminee", "CANCELLED": "Annulee", "UNCOVERED": "Non couverte",
}
SEV_RGB = {"LOW": BLUE, "MEDIUM": AMBER, "HIGH": RED, "CRITICAL": (176, 30, 30)}

_PUNCT = {
    "\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-",
    "\u2192": "->", "\u00a0": " ",
}


def _s(text):
    """Make any string safe for the latin-1 core fonts."""
    if text is None:
        return ""
    text = str(text)
    for bad, good in _PUNCT.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


class Doc(FPDF):
    """A4 document with the Panther letterhead and a confidentiality footer."""

    def __init__(self, subtitle=""):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.subtitle = subtitle
        self.set_margins(16, 34, 16)
        self.set_auto_page_break(True, margin=18)
        self.add_page()

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 26, "F")
        # paw-mark tile
        self.set_fill_color(*ORANGE)
        self.rect(16, 7, 11, 11, "F")
        self.set_fill_color(255, 255, 255)
        self.ellipse(19.5, 13, 4, 3, "F")
        for cx, cy in ((18, 10), (21, 8.6), (24, 8.6), (26, 10)):
            self.ellipse(cx - 0.7, cy - 0.7, 1.4, 1.4, "F")
        # wordmark
        self.set_xy(31, 7.5)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.cell(80, 5, _s("PANTHER HOME CARE"), new_x="LMARGIN", new_y="NEXT")
        self.set_xy(31, 13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(176, 188, 208)
        self.cell(90, 4, _s("Plateforme intelligente de gestion des soins a domicile"))
        # right column
        self.set_xy(118, 8.5)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(255, 255, 255)
        self.cell(76, 5, _s(self.subtitle), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_xy(118, 13.5)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(176, 188, 208)
        stamp = timezone.localtime().strftime("Genere le %d/%m/%Y a %H:%M")
        self.cell(76, 4, _s(stamp), align="R")
        self.set_y(34)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*LINE)
        self.line(16, self.get_y(), 194, self.get_y())
        self.set_y(-11)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(120, 4, _s("Confidentiel - Donnees de sante protegees (POPIA / Loi 18/035, RDC)"))
        self.cell(58, 4, _s(f"Page {self.page_no()}"), align="R")


# --- small drawing helpers ---------------------------------------------------
def _section(doc, title):
    doc.ln(3)
    doc.set_font("Helvetica", "B", 9)
    doc.set_text_color(*ORANGE)
    doc.cell(0, 5, _s(title.upper()), new_x="LMARGIN", new_y="NEXT")
    doc.set_draw_color(*LINE)
    doc.line(16, doc.get_y() + 0.5, 194, doc.get_y() + 0.5)
    doc.ln(2.5)
    doc.set_text_color(*INK)


def _pill(doc, text, rgb, x=None, y=None):
    if x is None:
        x = doc.get_x()
    if y is None:
        y = doc.get_y()
    doc.set_font("Helvetica", "B", 8)
    w = doc.get_string_width(_s(text)) + 6
    doc.set_fill_color(*rgb)
    doc.set_text_color(255, 255, 255)
    doc.rect(x, y, w, 5.5, "F")
    doc.set_xy(x, y + 0.7)
    doc.cell(w, 4, _s(text), align="C")
    doc.set_text_color(*INK)
    return w


def _kv(doc, label, value, lw=42, cw=None):
    cw = cw or (178 - lw)
    y = doc.get_y()
    doc.set_font("Helvetica", "", 9)
    doc.set_text_color(*MUTED)
    doc.set_xy(16, y)
    doc.cell(lw, 5, _s(label))
    doc.set_text_color(*INK)
    doc.set_font("Helvetica", "", 9)
    doc.multi_cell(cw, 5, _s(value or "-"))
    doc.set_y(max(doc.get_y(), y + 5))


def _table(doc, headers, rows, widths, aligns=None):
    aligns = aligns or ["L"] * len(headers)
    doc.set_font("Helvetica", "B", 8)
    doc.set_fill_color(*NAVY)
    doc.set_text_color(255, 255, 255)
    for h, w, a in zip(headers, widths, aligns):
        doc.cell(w, 6.5, _s(h), align=a, fill=True)
    doc.ln()
    doc.set_text_color(*INK)
    doc.set_font("Helvetica", "", 8)
    stripe = False
    for row in rows:
        if doc.get_y() > 262:
            doc.add_page()
            doc.set_font("Helvetica", "B", 8)
            doc.set_fill_color(*NAVY)
            doc.set_text_color(255, 255, 255)
            for h, w, a in zip(headers, widths, aligns):
                doc.cell(w, 6.5, _s(h), align=a, fill=True)
            doc.ln()
            doc.set_text_color(*INK)
            doc.set_font("Helvetica", "", 8)
        doc.set_fill_color(*(SOFT if stripe else (255, 255, 255)))
        for cell, w, a in zip(row, widths, aligns):
            doc.cell(w, 6, _s(cell), align=a, fill=True, border=0)
        doc.ln()
        doc.set_draw_color(*LINE)
        doc.line(16, doc.get_y(), 16 + sum(widths), doc.get_y())
        stripe = not stripe
    doc.ln(1)


def _note(doc, text):
    doc.set_fill_color(*SOFT)
    doc.set_text_color(*INK)
    doc.set_font("Helvetica", "", 8.5)
    doc.multi_cell(178, 5, _s(text), fill=True)
    doc.ln(1)


def _age(dob):
    if not dob:
        return None
    t = date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


# --- documents ---------------------------------------------------------------
def client_dossier_pdf(client):
    """The flagship Client 360 care dossier."""
    doc = Doc(subtitle="Dossier de soins - Client 360")

    # identity
    doc.set_font("Helvetica", "B", 15)
    doc.cell(120, 8, _s(f"{client.code} - {client.full_name}"))
    _pill(doc, f"Risque: {RISK_FR.get(client.risk_level, client.risk_level)}",
          RISK_RGB.get(client.risk_level, MUTED), x=150, y=doc.get_y() + 1)
    doc.ln(11)

    _section(doc, "Profil du beneficiaire")
    age = _age(client.date_of_birth)
    _kv(doc, "Nom complet", client.full_name)
    _kv(doc, "Age", f"{age} ans" if age is not None else "-")
    _kv(doc, "Adresse", client.address)
    _kv(doc, "Langue preferee", client.preferred_language)
    _kv(doc, "Type de soins", client.care_type)

    plan = getattr(client, "care_plan", None)
    if plan:
        _section(doc, "Plan de soins")
        if plan.summary:
            _note(doc, plan.summary)
        _kv(doc, "Duree de visite", f"{plan.visit_duration_minutes} minutes")
        skills = ", ".join(s.name for s in plan.required_skills.all())
        _kv(doc, "Competences requises", skills or "-")

    contacts = list(client.contacts.all())
    if contacts:
        _section(doc, "Contacts d'urgence")
        _table(doc, ["Nom", "Relation", "Telephone"],
               [[c.name, c.relationship or "-", c.phone] for c in contacts],
               [70, 58, 50])

    visits = list(client.visits.select_related("caregiver").order_by("-scheduled_start")[:10])
    if visits:
        _section(doc, "Historique des visites (10 dernieres)")
        rows = []
        for v in visits:
            rows.append([
                timezone.localtime(v.scheduled_start).strftime("%d/%m/%Y %H:%M"),
                v.caregiver.code if v.caregiver else "Non affecte",
                STATUS_FR.get(v.status, v.status),
                f"{v.minutes_late} min" if v.minutes_late else "-",
            ])
        _table(doc, ["Date", "Soignant", "Statut", "Retard"], rows,
               [42, 46, 46, 44], ["L", "L", "L", "R"])

    reports = list(CareReport.objects.filter(visit__client=client)
                   .select_related("caregiver").order_by("-created_at")[:8])
    if reports:
        _section(doc, "Rapports de soins recents")
        moods = dict(Mood.choices)
        rows = []
        for r in reports:
            rows.append([
                timezone.localtime(r.created_at).strftime("%d/%m %H:%M"),
                r.caregiver.code if r.caregiver else "-",
                _s(moods.get(r.mood, str(r.mood))),
                r.blood_pressure or "-",
                r.pulse or "-",
            ])
        _table(doc, ["Date", "Soignant", "Humeur", "Tension", "Pouls"], rows,
               [30, 40, 40, 34, 34])

    flags = [r for r in reports if r.ai_flagged]
    if flags:
        _section(doc, "Preoccupations detectees par l'IA")
        doc.set_font("Helvetica", "", 7.5)
        doc.set_text_color(*MUTED)
        doc.multi_cell(178, 4, _s(
            "Signalements automatiques a des fins de revue humaine. "
            "Ce ne sont pas des diagnostics medicaux."))
        doc.ln(1)
        for r in flags:
            doc.set_fill_color(254, 246, 246)
            doc.set_draw_color(246, 212, 212)
            y = doc.get_y()
            doc.rect(16, y, 178, 9, "DF")
            doc.set_xy(19, y + 1.4)
            doc.set_text_color(*RED)
            doc.set_font("Helvetica", "B", 8.5)
            doc.cell(174, 4, _s(timezone.localtime(r.created_at).strftime("%d/%m/%Y %H:%M")
                     + f"  -  {r.caregiver.code if r.caregiver else 'Soignant'}"),
                     new_x="LMARGIN", new_y="NEXT")
            doc.set_x(19)
            doc.set_text_color(*INK)
            doc.set_font("Helvetica", "", 8.5)
            doc.cell(174, 4, _s(r.ai_concern or "Preoccupation potentielle - revue recommandee."))
            doc.set_y(y + 11)

    incidents = list(client.incidents.all()[:8])
    if incidents:
        _section(doc, "Incidents")
        _table(doc, ["Date", "Titre", "Gravite", "Statut"],
               [[timezone.localtime(i.created_at).strftime("%d/%m/%Y"),
                 i.title,
                 i.get_severity_display(),
                 i.get_status_display()] for i in incidents],
               [30, 78, 36, 34])

    return bytes(doc.output())


def care_report_pdf(report):
    """A single post-visit care report."""
    doc = Doc(subtitle="Rapport de soins")
    v = report.visit
    client = v.client

    doc.set_font("Helvetica", "B", 15)
    doc.cell(0, 8, _s(f"Rapport de visite - {client.code}"), new_x="LMARGIN", new_y="NEXT")
    doc.ln(3)

    _section(doc, "Visite")
    _kv(doc, "Beneficiaire", f"{client.code} - {client.full_name}")
    _kv(doc, "Soignant", report.caregiver.full_name if report.caregiver else "-")
    _kv(doc, "Date et heure", timezone.localtime(report.created_at).strftime("%d/%m/%Y a %H:%M"))
    _kv(doc, "Creneau planifie",
        timezone.localtime(v.scheduled_start).strftime("%d/%m/%Y %H:%M")
        + " - " + timezone.localtime(v.scheduled_end).strftime("%H:%M"))

    _section(doc, "Observations")
    moods = dict(Mood.choices)
    _kv(doc, "Humeur", _s(moods.get(report.mood, str(report.mood))))
    _kv(doc, "Tension arterielle", report.blood_pressure)
    _kv(doc, "Pouls", report.pulse)

    tasks = report.tasks_completed or []
    if tasks:
        _section(doc, "Taches realisees")
        doc.set_font("Helvetica", "", 9)
        for t in tasks:
            y = doc.get_y()
            doc.set_draw_color(*GREEN)
            doc.set_line_width(0.6)
            doc.line(17, y + 3, 18.6, y + 4.4)
            doc.line(18.6, y + 4.4, 21, y + 1.6)
            doc.set_line_width(0.2)
            doc.set_text_color(*INK)
            doc.set_x(24)
            doc.cell(0, 5, _s(t), new_x="LMARGIN", new_y="NEXT")
        doc.ln(1)

    if report.notes:
        _section(doc, "Notes du soignant")
        _note(doc, report.notes)

    if report.ai_flagged:
        _section(doc, "Analyse IA")
        doc.set_fill_color(254, 246, 246)
        doc.set_draw_color(246, 212, 212)
        y = doc.get_y()
        doc.rect(16, y, 178, 16, "DF")
        doc.set_xy(19, y + 2)
        doc.set_text_color(*RED)
        doc.set_font("Helvetica", "B", 9)
        doc.cell(0, 5, _s("Preoccupation potentielle detectee"), new_x="LMARGIN", new_y="NEXT")
        doc.set_x(19)
        doc.set_text_color(*INK)
        doc.set_font("Helvetica", "", 8.5)
        doc.multi_cell(172, 4.5, _s(
            (report.ai_concern or "Revue professionnelle recommandee.")
            + " Signalement automatique - ne constitue pas un diagnostic medical."))
        doc.set_y(y + 18)

    return bytes(doc.output())


def daily_brief_pdf(context=None):
    """The coordinator's daily operations brief."""
    doc = Doc(subtitle="Resume operationnel du jour")
    brief = (context or {}).get("brief") if context else daily_brief()
    if brief is None:
        brief = daily_brief()

    now = timezone.localtime()
    doc.set_font("Helvetica", "B", 15)
    doc.cell(0, 8, _s(now.strftime("Brief du %d/%m/%Y")), new_x="LMARGIN", new_y="NEXT")
    doc.ln(2)

    # KPI band
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timezone.timedelta(days=1)
    todays = Visit.objects.filter(scheduled_start__gte=day_start, scheduled_start__lt=day_end)
    open_inc = Incident.objects.exclude(status=IncidentStatus.RESOLVED).count()
    kpis = [
        ("Dans les temps", f"{brief.get('on_schedule_pct', 0)}%", GREEN),
        ("Confirmes", str(brief.get("confirmed", 0)), BLUE),
        ("En retard", str(brief.get("late", 0)), AMBER),
        ("Non couvertes", str(brief.get("uncovered", 0)), RED),
        ("Incidents ouverts", str(open_inc), (176, 30, 30)),
    ]
    x = 16
    w = 35.2
    y = doc.get_y()
    for label, val, rgb in kpis:
        doc.set_draw_color(*LINE)
        doc.rect(x, y, w - 2, 20, "D")
        doc.set_xy(x, y + 3)
        doc.set_text_color(*MUTED)
        doc.set_font("Helvetica", "", 7)
        doc.cell(w - 2, 4, _s(label), align="C")
        doc.set_xy(x, y + 8)
        doc.set_text_color(*rgb)
        doc.set_font("Helvetica", "B", 17)
        doc.cell(w - 2, 8, _s(val), align="C")
        x += w
    doc.set_y(y + 24)
    doc.set_text_color(*INK)

    _section(doc, "Synthese IA")
    _note(doc, brief.get("summary", ""))

    uncovered = [v for v in todays.select_related("client") if v.is_uncovered]
    if uncovered:
        _section(doc, "Visites non couvertes")
        _table(doc, ["Client", "Creneau", "Type de soins"],
               [[v.client.code,
                 timezone.localtime(v.scheduled_start).strftime("%H:%M")
                 + "-" + timezone.localtime(v.scheduled_end).strftime("%H:%M"),
                 v.client.care_type or "-"] for v in uncovered],
               [46, 52, 80])

    flagged = list(CareReport.objects.filter(ai_flagged=True, created_at__gte=day_start)
                   .select_related("visit__client")[:10])
    if flagged:
        _section(doc, "Clients a surveiller (signalements IA)")
        _table(doc, ["Client", "Preoccupation"],
               [[r.visit.client.code, (r.ai_concern or "-")[:70]] for r in flagged],
               [40, 138])

    crit = list(Incident.objects.filter(severity="CRITICAL")
                .exclude(status=IncidentStatus.RESOLVED).select_related("client")[:10])
    if crit:
        _section(doc, "Incidents critiques")
        _table(doc, ["Client", "Incident", "Statut"],
               [[i.client.code if i.client else "-", i.title, i.get_status_display()]
                for i in crit],
               [40, 96, 42])

    return bytes(doc.output())


def weekly_report_pdf():
    """A weekly operations summary for the back office."""
    from datetime import timedelta
    from django.db.models import Avg
    from caregivers.models import Caregiver
    from reports.models import CareReport

    now = timezone.localtime()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=7)
    doc = Doc(subtitle="Rapport hebdomadaire d'opérations")

    doc.set_font("Helvetica", "B", 15)
    doc.cell(0, 8, _s(monday.strftime("Semaine du %d/%m") + sunday.strftime(" au %d/%m/%Y")),
             new_x="LMARGIN", new_y="NEXT")
    doc.ln(3)

    wk = Visit.objects.filter(scheduled_start__gte=monday, scheduled_start__lt=sunday)
    scheduled = wk.exclude(status=VisitStatus.CANCELLED).count()
    completed = wk.filter(status=VisitStatus.COMPLETED).count()
    uncovered = wk.filter(status=VisitStatus.UNCOVERED).count()
    on_sched = round(100 * completed / scheduled) if scheduled else 0
    inc = Incident.objects.filter(created_at__gte=monday, created_at__lt=sunday).count()
    avg_mood = CareReport.objects.filter(created_at__gte=monday).aggregate(m=Avg("mood"))["m"] or 0

    _section(doc, "Indicateurs de la semaine")
    _kv(doc, "Visites planifiées", str(scheduled))
    _kv(doc, "Visites terminées", f"{completed}  ({on_sched}% dans les temps)")
    _kv(doc, "Visites non couvertes", str(uncovered))
    _kv(doc, "Incidents déclarés", str(inc))
    _kv(doc, "Satisfaction moyenne", f"{round(avg_mood * 20)}%")

    # Top caregivers by hours this week
    load = []
    for cg in Caregiver.objects.filter(active=True).prefetch_related("visits"):
        secs = sum((v.check_out_at - v.check_in_at).total_seconds()
                   for v in cg.visits.filter(status=VisitStatus.COMPLETED,
                                             scheduled_start__gte=monday, scheduled_start__lt=sunday)
                   if v.check_in_at and v.check_out_at)
        if secs:
            load.append((cg.code, cg.full_name, round(secs / 3600, 1)))
    load.sort(key=lambda x: x[2], reverse=True)
    if load:
        _section(doc, "Soignants — heures réalisées (top 10)")
        _table(doc, ["Soignant", "Nom", "Heures"],
               [[c, n, f"{h} h"] for c, n, h in load[:10]],
               [40, 90, 48], ["L", "L", "R"])

    crit = list(Incident.objects.filter(created_at__gte=monday, severity="CRITICAL")
                .select_related("client")[:10])
    if crit:
        _section(doc, "Incidents critiques")
        _table(doc, ["Date", "Client", "Incident"],
               [[timezone.localtime(i.created_at).strftime("%d/%m"),
                 i.client.code if i.client else "-", i.title] for i in crit],
               [30, 40, 108])

    return bytes(doc.output())


def invoice_pdf(invoice):
    """A professional, printable single invoice."""
    from accounts.models import AgencySettings
    cfg = AgencySettings.get()
    cur = cfg.currency
    doc = Doc(subtitle="Facture")

    doc.set_font("Helvetica", "B", 20)
    doc.cell(0, 10, _s(f"FACTURE {cfg.invoice_prefix}-{invoice.id:05d}"), new_x="LMARGIN", new_y="NEXT")
    doc.ln(2)

    # Agency + client blocks
    y0 = doc.get_y()
    doc.set_font("Helvetica", "B", 10)
    doc.cell(90, 6, _s("Émetteur"), new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", "", 10)
    for line in [cfg.agency_name, cfg.address, cfg.contact_email, cfg.contact_phone]:
        if line:
            doc.cell(90, 5, _s(line), new_x="LMARGIN", new_y="NEXT")
    y1 = doc.get_y()

    doc.set_xy(110, y0)
    doc.set_font("Helvetica", "B", 10)
    doc.cell(90, 6, _s("Client"), new_x="LMARGIN", new_y="NEXT")
    doc.set_x(110)
    doc.set_font("Helvetica", "", 10)
    doc.cell(90, 5, _s(f"{invoice.client.code} — {invoice.client.full_name}"), new_x="LMARGIN", new_y="NEXT")
    if invoice.client.address:
        doc.set_x(110)
        doc.cell(90, 5, _s(invoice.client.address), new_x="LMARGIN", new_y="NEXT")
    doc.set_y(max(y1, doc.get_y()) + 6)

    _kv(doc, "Période", invoice.period)
    _kv(doc, "Date d'émission", invoice.issued_date.strftime("%d/%m/%Y"))
    if invoice.due_date:
        _kv(doc, "Échéance", invoice.due_date.strftime("%d/%m/%Y"))
    doc.ln(3)

    hours = float(invoice.hours or 0)
    amount = float(invoice.amount or 0)
    rate = round(amount / hours, 2) if hours else 0
    tax_rate = float(cfg.tax_rate or 0)
    subtotal = amount
    tax = round(subtotal * tax_rate / 100, 2)
    total = subtotal + tax

    _section(doc, "Détail")
    _table(doc, ["Description", "Heures", "Tarif", "Montant"],
           [[f"Services de soins — {invoice.period}", f"{hours:g}",
             f"{rate:g} {cur}", f"{subtotal:.2f} {cur}"]],
           [90, 30, 30, 38], ["L", "R", "R", "R"])

    doc.ln(2)
    doc.set_font("Helvetica", "", 10)
    doc.cell(150, 6, _s("Sous-total"), align="R")
    doc.cell(38, 6, _s(f"{subtotal:.2f} {cur}"), align="R", new_x="LMARGIN", new_y="NEXT")
    if tax_rate:
        doc.cell(150, 6, _s(f"TVA ({tax_rate:g}%)"), align="R")
        doc.cell(38, 6, _s(f"{tax:.2f} {cur}"), align="R", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", "B", 12)
    doc.cell(150, 8, _s("TOTAL"), align="R")
    doc.cell(38, 8, _s(f"{total:.2f} {cur}"), align="R", new_x="LMARGIN", new_y="NEXT")
    doc.ln(4)

    # Status stamp
    paid = invoice.status == "PAID"
    doc.set_font("Helvetica", "B", 13)
    if paid:
        doc.set_text_color(20, 120, 60)
        label = "PAYÉE" + (f" — le {invoice.paid_on:%d/%m/%Y}" if invoice.paid_on else "")
    else:
        doc.set_text_color(190, 40, 40)
        label = "NON PAYÉE" if invoice.status != "OVERDUE" else "EN RETARD"
    doc.cell(0, 9, _s(label), new_x="LMARGIN", new_y="NEXT")
    doc.set_text_color(20, 30, 55)

    return bytes(doc.output())


def payslip_pdf(caregiver, m_start, m_end, label):
    """A staff payslip — hours worked in a period × pay rate."""
    from accounts.models import AgencySettings
    cfg = AgencySettings.get()
    cur = cfg.currency
    doc = Doc(subtitle="Fiche de paie")

    hours = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                if v.check_in_at and v.check_out_at
                else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
                for v in caregiver.visits.filter(status=VisitStatus.COMPLETED,
                                                 scheduled_start__gte=m_start, scheduled_start__lt=m_end))
    hours = round(hours, 1)
    rate = float(caregiver.pay_rate or 0)
    gross = round(hours * rate, 2)

    doc.set_font("Helvetica", "B", 20)
    doc.cell(0, 10, _s("FICHE DE PAIE"), new_x="LMARGIN", new_y="NEXT")
    doc.ln(2)

    y0 = doc.get_y()
    doc.set_font("Helvetica", "B", 10); doc.cell(90, 6, _s("Employeur"), new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Helvetica", "", 10)
    for line in [cfg.agency_name, cfg.address]:
        if line:
            doc.cell(90, 5, _s(line), new_x="LMARGIN", new_y="NEXT")
    y1 = doc.get_y()
    doc.set_xy(110, y0)
    doc.set_font("Helvetica", "B", 10); doc.cell(90, 6, _s("Soignant"), new_x="LMARGIN", new_y="NEXT")
    doc.set_x(110); doc.set_font("Helvetica", "", 10)
    doc.cell(90, 5, _s(f"{caregiver.code} — {caregiver.full_name}"), new_x="LMARGIN", new_y="NEXT")
    if caregiver.phone:
        doc.set_x(110); doc.cell(90, 5, _s(caregiver.phone), new_x="LMARGIN", new_y="NEXT")
    doc.set_y(max(y1, doc.get_y()) + 6)

    _kv(doc, "Période", label)
    _kv(doc, "Date d'émission", timezone.localdate().strftime("%d/%m/%Y"))
    doc.ln(3)

    _section(doc, "Détail")
    _table(doc, ["Description", "Heures", "Taux", "Montant"],
           [[f"Heures de soins — {label}", f"{hours:g}", f"{rate:g} {cur}", f"{gross:.2f} {cur}"]],
           [90, 30, 30, 38], ["L", "R", "R", "R"])
    doc.ln(2)
    doc.set_font("Helvetica", "B", 12)
    doc.cell(150, 8, _s("NET À PAYER"), align="R")
    doc.cell(38, 8, _s(f"{gross:.2f} {cur}"), align="R", new_x="LMARGIN", new_y="NEXT")
    return bytes(doc.output())
