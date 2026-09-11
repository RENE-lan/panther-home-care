"""Seed realistic demo data that reproduces the pitch scenario."""
import random
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, Role
from caregivers.models import Caregiver, Skill, Certification, Availability, Applicant, ApplicationStage
from clients.models import Client, EmergencyContact, CarePlan, CareTask, RiskLevel
from incidents.models import Incident, Severity, IncidentStatus
from notifications.models import Notification, AlertLevel
from reports.models import CareReport
from scheduling.models import Visit, VisitStatus
from ai.services import scan_report_for_risk

# Lubumbashi, RDC — the mockup's market.
CITY_LAT, CITY_LNG = -11.66, 27.48


class Command(BaseCommand):
    help = "Populate the database with demo data for Panther Home Care."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty", action="store_true",
            help="Only seed when the database is empty; preserves existing accounts and data.")

    def handle(self, *args, **opts):
        if opts.get("if_empty") and (Client.objects.exists()
                                     or User.objects.filter(is_superuser=False).exists()):
            self.stdout.write("Données déjà présentes — seed ignoré (--if-empty).")
            return
        self.stdout.write("Réinitialisation des données de démonstration…")
        for m in (Notification, CareReport, Incident, Visit, CareTask, CarePlan,
                  EmergencyContact, Client, Certification, Availability, Applicant, Caregiver, Skill):
            m.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        # --- Coordinator login (the "René" in the mockup) ---
        coord, _ = User.objects.get_or_create(
            username="rene", defaults={"first_name": "René", "last_name": "Bakenga",
                                       "role": Role.COORDINATOR, "email": "rene@panthergroup.cd"})
        coord.is_staff = True          # so the Paramètres / Recrutement admin links open
        coord.is_superuser = True
        coord.set_password("panther123"); coord.save()
        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(
                user=coord, email=coord.email,
                defaults={"verified": True, "primary": True})
        except Exception:
            pass

        # --- Skills ---
        skill_names = ["Personnes âgées", "Démence", "Mobilité réduite", "Soins post-opératoires",
                       "Diabète", "Hygiène personnelle", "Accompagnement"]
        skills = {n: Skill.objects.create(name=n) for n in skill_names}

        # --- Caregivers (Soignant #001…#030) ---
        langs = ["Français", "Français, Swahili", "Français, Anglais", "Swahili"]
        caregivers = []
        for i in range(1, 31):
            cg = Caregiver.objects.create(
                code=f"Soignant #{i:03d}",
                first_name=random.choice(["Marie", "Jean", "Grace", "Patrick", "Nadine",
                                          "Josué", "Esther", "Daniel", "Sarah", "Éric"]),
                last_name=random.choice(["Kabila", "Mwamba", "Ilunga", "Tshala", "Banza",
                                         "Kalonji", "Mutombo", "Ngoy", "Kasongo"]),
                languages=random.choice(langs),
                home_latitude=CITY_LAT + random.uniform(-0.05, 0.05),
                home_longitude=CITY_LNG + random.uniform(-0.05, 0.05),
                reliability_score=random.randint(78, 97),
                punctuality_score=random.randint(80, 98),
            )
            cg.skills.set(random.sample(list(skills.values()), random.randint(2, 4)))
            caregivers.append(cg)

        # Pin the mockup's hero recommendation: Soignant #027, elderly-care, 94%, close by.
        hero = next(c for c in caregivers if c.code == "Soignant #027")
        hero.skills.add(skills["Personnes âgées"])
        hero.reliability_score = 94
        hero.home_latitude, hero.home_longitude = CITY_LAT + 0.02, CITY_LNG + 0.02
        hero.save()
        Certification.objects.create(caregiver=hero, name="Certificat soins gériatriques",
                                     expires_on=timezone.localdate() + timedelta(days=200))

        # Certifications across the team with varied expiry (for the Conformité monitor)
        cert_names = ["Premiers secours", "RCP / Réanimation", "Hygiène & sécurité",
                      "Manutention des patients", "Soins gériatriques"]
        today = timezone.localdate()
        for i, cg in enumerate(caregivers):
            name = cert_names[i % len(cert_names)]
            if i % 7 == 0:
                exp = today - timedelta(days=random.randint(5, 60))     # expired
            elif i % 3 == 0:
                exp = today + timedelta(days=random.randint(8, 55))     # expiring soon
            else:
                exp = today + timedelta(days=random.randint(120, 400))  # valid
            Certification.objects.create(
                caregiver=cg, name=name,
                issued_on=exp - timedelta(days=365), expires_on=exp)

        # --- Clients (Client #001…#030) ---
        care_types = ["Personnes âgées", "Démence", "Mobilité réduite", "Diabète"]
        clients = []
        for i in range(1, 31):
            ct = random.choice(care_types)
            c = Client.objects.create(
                code=f"Client #{i:03d}",
                first_name=random.choice(["Antoine", "Bernadette", "Célestin", "Odette",
                                          "Léon", "Micheline", "Georges", "Pauline"]),
                last_name=random.choice(["Mukendi", "Ntumba", "Kabongo", "Lubaba", "Kanku"]),
                address=f"{random.randint(1,220)} Av. {random.choice(['Kasavubu','Mama Yemo','Lumumba','Kimbangu'])}, Lubumbashi",
                latitude=CITY_LAT + random.uniform(-0.04, 0.04),
                longitude=CITY_LNG + random.uniform(-0.04, 0.04),
                preferred_language="Français",
                care_type=ct,
                risk_level=random.choice([RiskLevel.LOW, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]),
            )
            EmergencyContact.objects.create(client=c, name="Contact famille",
                                            relationship="Fils/Fille", phone="+243 8XX XXX XXX",
                                            is_primary=True)
            plan = CarePlan.objects.create(client=c, summary=f"Plan de soins — {ct}",
                                           visit_duration_minutes=240)
            plan.required_skills.add(skills[ct] if ct in skills else skills["Accompagnement"])
            for order, label in enumerate(["Hygiène personnelle", "Médication", "Repas",
                                           "Mobilité", "Signes vitaux"]):
                CareTask.objects.create(care_plan=plan, label=label, order=order)
            clients.append(c)

        # --- Today's visits ---
        # Spread visits across the day. Anything already in the past is treated as
        # completed (with a report) so the board isn't full of stale "late" rows;
        # we then inject exactly one deliberate late visit for the ATTENTION panel.
        now = timezone.localtime()
        day = now.replace(hour=8, minute=0, second=0, microsecond=0)
        for idx, c in enumerate(clients):
            start = day + timedelta(hours=(idx % 10))
            v = Visit.objects.create(
                client=c, caregiver=random.choice(caregivers),
                scheduled_start=start, scheduled_end=start + timedelta(hours=4),
                status=VisitStatus.SCHEDULED,
            )
            if v.scheduled_start < now:
                late = random.choice([0, 0, 0, 0, 5, 8, 12, 18])
                v.check_in_at = start + timedelta(minutes=late)
                v.check_out_at = start + timedelta(hours=4)
                v.check_in_lat, v.check_in_lng = c.latitude, c.longitude
                v.status = VisitStatus.COMPLETED
                v.save(update_fields=["check_in_at", "check_out_at",
                                      "check_in_lat", "check_in_lng", "status"])
                mood = random.choice([5, 4, 4, 3, 2])
                notes = "Tout s'est bien passé. Le client a pris ses médicaments." if mood >= 4 else \
                        "Le client a mentionné des étourdissements à deux reprises cette semaine."
                r = CareReport.objects.create(visit=v, caregiver=v.caregiver, notes=notes,
                                              mood=mood, blood_pressure="120/80", pulse="72 bpm",
                                              tasks_completed=["Hygiène personnelle", "Médication", "Repas"])
                scan_report_for_risk(r)

        # The hero scenario: Client #014, 14:00–18:00, uncovered.
        c14 = Client.objects.get(code="Client #014")
        c14.care_type = "Personnes âgées"; c14.save()
        c14.care_plan.required_skills.set([skills["Personnes âgées"]])
        hero_start = day.replace(hour=14)
        hero_end = day.replace(hour=18)
        Visit.objects.filter(client=c14, scheduled_start__gte=day).delete()
        # Free the hero caregiver during that window so it's an eligible recommendation.
        hero.visits.filter(scheduled_start__lt=hero_end, scheduled_end__gt=hero_start).delete()
        Visit.objects.create(client=c14, caregiver=None,
                             scheduled_start=hero_start, scheduled_end=hero_end,
                             status=VisitStatus.UNCOVERED)

        # One deliberate late visit for the ATTENTION panel (27 min, as in the mockup):
        # scheduled 27 min ago, assigned, but no check-in yet.
        late_client = Client.objects.get(code="Client #031") if Client.objects.filter(
            code="Client #031").exists() else clients[-1]
        Visit.objects.create(
            client=late_client, caregiver=hero if hero.code != "Soignant #027" else caregivers[0],
            scheduled_start=now - timedelta(minutes=27),
            scheduled_end=now + timedelta(hours=3, minutes=33),
            status=VisitStatus.SCHEDULED,
        )

        # Backdate most client/caregiver records so "new this week" trends are realistic
        for i, c in enumerate(Client.objects.all()):
            d = random.randint(0, 5) if i < 3 else random.randint(20, 180)
            Client.objects.filter(pk=c.pk).update(created_at=day - timedelta(days=d))
        for i, cg in enumerate(Caregiver.objects.all()):
            d = random.randint(0, 6) if i < 2 else random.randint(20, 200)
            Caregiver.objects.filter(pk=cg.pk).update(created_at=day - timedelta(days=d))

        # --- 30 days of history so analytics/trends look real ---
        concern_notes = [
            "Le client a mentionné des étourdissements à deux reprises.",
            "Léger vertige signalé ce matin, à surveiller.",
            "Douleur au genou rapportée, mobilité réduite aujourd'hui.",
            "Client un peu confus en fin de visite.",
        ]
        ok_notes = [
            "Tout s'est bien passé. Médicaments pris à l'heure.",
            "Visite sans incident. Bonne humeur générale.",
            "Repas pris normalement, moral positif.",
            "RAS. Constantes stables.",
        ]
        hist_visits, hist_reports = [], []
        for d in range(1, 31):
            base = day - timedelta(days=d)
            n = random.randint(14, 26)
            for _ in range(n):
                c = random.choice(clients)
                cg = random.choice(caregivers)
                hour = random.randint(7, 17)
                s = base.replace(hour=hour, minute=random.choice([0, 15, 30]))
                dur = random.choice([2, 3, 4])
                late_min = random.choice([0, 0, 0, 0, 8, 15, 22])
                hist_visits.append(Visit(
                    client=c, caregiver=cg, scheduled_start=s,
                    scheduled_end=s + timedelta(hours=dur),
                    status=VisitStatus.COMPLETED,
                    check_in_at=s + timedelta(minutes=late_min),
                    check_out_at=s + timedelta(hours=dur),
                    check_in_lat=c.latitude, check_in_lng=c.longitude,
                ))
        Visit.objects.bulk_create(hist_visits, batch_size=500)

        # Reports for a subset of historical visits (drives mood + AI-flag trends)
        for v in hist_visits:
            if random.random() < 0.55:
                concern = random.random() < 0.14
                mood = random.choice([2, 3]) if concern else random.choice([5, 4, 4, 3])
                notes = random.choice(concern_notes if concern else ok_notes)
                r = CareReport(
                    visit=v, caregiver=v.caregiver, notes=notes, mood=mood,
                    blood_pressure=random.choice(["118/78", "120/80", "126/82", "134/86"]),
                    pulse=f"{random.randint(64, 82)} bpm",
                    tasks_completed=["Hygiène personnelle", "Médication", "Repas"],
                )
                r.created_at_backdate = v.scheduled_end
                hist_reports.append(r)
        CareReport.objects.bulk_create(hist_reports, batch_size=500)
        # Backdate report timestamps + run the AI risk pass on each
        for r in hist_reports:
            CareReport.objects.filter(pk=r.pk).update(created_at=r.created_at_backdate)
            r.created_at = r.created_at_backdate
            scan_report_for_risk(r)

        # Scattered historical incidents across the month
        for d in range(0, 30, 3):
            when = day - timedelta(days=d, hours=random.randint(0, 8))
            inc = Incident.objects.create(
                client=random.choice(clients),
                title=random.choice(["Retard de médication", "Plainte client",
                                      "Visite écourtée", "Matériel manquant"]),
                severity=random.choice([Severity.LOW, Severity.MEDIUM, Severity.MEDIUM,
                                        Severity.HIGH]),
                status=random.choice([IncidentStatus.RESOLVED, IncidentStatus.RESOLVED,
                                      IncidentStatus.OPEN]))
            Incident.objects.filter(pk=inc.pk).update(created_at=when)

        # --- Incidents ---
        Incident.objects.create(client=random.choice(clients), title="Chute signalée à domicile",
                                severity=Severity.CRITICAL, status=IncidentStatus.ESCALATED,
                                description="Chute rapportée par la famille — escalade au conseiller clinique.")
        for _ in range(3):
            Incident.objects.create(client=random.choice(clients),
                                    title=random.choice(["Retard de médication", "Plainte client",
                                                         "Visite écourtée"]),
                                    severity=random.choice([Severity.LOW, Severity.MEDIUM]),
                                    status=IncidentStatus.OPEN)

        # --- Notifications for the coordinator ---
        Notification.objects.create(recipient=coord, level=AlertLevel.CRITICAL,
                                    title="Visite non couverte — Client #014",
                                    body="14:00–18:00 · IA recommande Soignant #027.")
        Notification.objects.create(recipient=coord, level=AlertLevel.ATTENTION,
                                    title="Soignant en retard de 27 min")

        # --- Caregiver self-service demo: a caregiver login, environment attributes,
        #     and a set of open (unfilled) visits over the next 45 days ------------------
        demo_cg = caregivers[0]  # Soignant #001
        demo_cg.gender = "F"
        demo_cg.comfortable_with_pets = False       # so pet households score lower for her
        demo_cg.comfortable_with_smoking = False
        demo_cg.home_latitude, demo_cg.home_longitude = CITY_LAT + 0.01, CITY_LNG + 0.01
        demo_cg.save()
        cg_user, _ = User.objects.get_or_create(
            username="soignant",
            defaults={"first_name": demo_cg.first_name, "last_name": demo_cg.last_name,
                      "email": "soignant@panthergroup.cd", "role": Role.CAREGIVER})
        cg_user.set_password("soignant123"); cg_user.save()
        demo_cg.user = cg_user; demo_cg.save(update_fields=["user"])
        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(
                user=cg_user, email=cg_user.email,
                defaults={"verified": True, "primary": True})
        except Exception:
            pass

        # Give some clients environment attributes so match scores vary meaningfully.
        for i, c in enumerate(clients):
            c.has_pets = (i % 4 == 0)
            c.smoking_household = (i % 6 == 0)
            c.caregiver_gender_preference = "FEMALE" if i % 5 == 0 else "ANY"
            c.save(update_fields=["has_pets", "smoking_household", "caregiver_gender_preference"])

        # Open visits over the next 45 days (unassigned → the marketplace).
        open_visits = []
        for d in range(1, 46):
            if d % 2:  # every other day
                continue
            base = day + timedelta(days=d)
            for _ in range(random.randint(1, 3)):
                c = random.choice(clients)
                hour = random.choice([8, 9, 10, 12, 14, 16])
                s = base.replace(hour=hour, minute=0)
                open_visits.append(Visit(
                    client=c, caregiver=None, scheduled_start=s,
                    scheduled_end=s + timedelta(hours=random.choice([2, 3, 4])),
                    status=VisitStatus.UNCOVERED))
        Visit.objects.bulk_create(open_visits, batch_size=200)

        # EVV demo: assign the demo caregiver upcoming visits to clock in/out.
        for off, hour in [(0, 9), (0, 14), (1, 10), (1, 15), (2, 11)]:
            s = (day + timedelta(days=off)).replace(hour=hour, minute=0)
            Visit.objects.create(client=random.choice(clients), caregiver=demo_cg,
                                 scheduled_start=s, scheduled_end=s + timedelta(hours=2),
                                 status=VisitStatus.SCHEDULED)

        # A demo recurring schedule ("master week")
        from scheduling.models import RecurringSchedule
        rs = RecurringSchedule.objects.create(
            client=clients[13], caregiver=demo_cg, weekdays="0,2,4",
            start_time=day.replace(hour=9).time(), duration_minutes=180,
            start_date=(day + timedelta(days=1)).date(), weeks=4)
        rs.generate()

        # --- Family portal demo: a family login linked to Client #014, invoices, messages
        from clients.models import Invoice, Message
        from datetime import date
        fam_client = clients[13]  # Client #014
        fam_user, _ = User.objects.get_or_create(
            username="famille",
            defaults={"first_name": "Marie", "last_name": fam_client.last_name,
                      "email": "famille@panthergroup.cd", "role": Role.FAMILY})
        fam_user.set_password("famille123"); fam_user.save()
        fam_client.family_user = fam_user
        fam_client.save(update_fields=["family_user"])
        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(user=fam_user, email=fam_user.email,
                                               defaults={"verified": True, "primary": True})
        except Exception:
            pass
        Invoice.objects.bulk_create([
            Invoice(client=fam_client, period="Juillet 2026", hours=64, amount="512.00",
                    status=Invoice.Status.PAID, issued_date=date(2026, 8, 1), due_date=date(2026, 8, 15)),
            Invoice(client=fam_client, period="Août 2026", hours=72, amount="576.00",
                    status=Invoice.Status.DUE, issued_date=date(2026, 9, 1), due_date=date(2026, 9, 15)),
        ])
        Message.objects.create(client=fam_client, sender=fam_user, from_agency=False,
                               body="Bonjour, ma mère préfère les visites le matin si possible. Merci !")
        Message.objects.create(client=fam_client, sender=coord, from_agency=True,
                               body="Bonjour Marie, c'est noté — nous privilégierons les créneaux du matin. Belle journée.")

        # --- Clinical tracking demo: a few care concerns with progress updates ---
        from clients.models import CareConcern
        _concern_defs = [
            (clients[3], "WOUND", "talon gauche", 3, "OPEN",
             [("Plaie de 4 cm × 3 cm, stade II.", "4 cm × 3 cm", "OPEN"),
              ("Bourgeonnement visible, légère amélioration.", "3 cm × 2 cm", "IMPROVING")]),
            (clients[9], "PAIN", "genou droit", 2, "IMPROVING",
             [("Douleur signalée à la mobilisation.", "", "OPEN"),
              ("Douleur réduite avec le repos et la kiné.", "", "IMPROVING")]),
            (clients[13], "SKIN", "sacrum", 2, "OPEN",
             [("Rougeur persistante, risque d'escarre.", "", "OPEN")]),
            (clients[20], "MOBILITY", "", 1, "RESOLVED",
             [("Difficulté aux transferts.", "", "OPEN"),
              ("Autonomie retrouvée avec aide technique.", "", "RESOLVED")]),
        ]
        for cl, ctype, loc, sev, status, ups in _concern_defs:
            con = CareConcern.objects.create(
                client=cl, concern_type=ctype, location=loc, severity=sev, status=status,
                opened_on=day.date() - timedelta(days=random.randint(10, 40)), created_by=coord)
            for i, (note, meas, st) in enumerate(ups):
                u = con.updates.create(note=note, measurement=meas, status=st, created_by=coord)
                ConcernUpdate = con.updates.model
                ConcernUpdate.objects.filter(pk=u.pk).update(
                    created_at=day - timedelta(days=(len(ups) - i) * 7))
            if status == "RESOLVED":
                con.resolved_on = day.date(); con.save(update_fields=["resolved_on"])

        # --- Talent Hub pipeline ---
        for stage in [ApplicationStage.APPLICATION, ApplicationStage.SCREENING,
                      ApplicationStage.INTERVIEW, ApplicationStage.TRAINING]:
            Applicant.objects.create(first_name="Candidat", last_name=stage.label, stage=stage)

        # --- Time clock demo: a few staff punches (incl. one still open) ---
        from accounts.models import TimeEntry
        from datetime import time as _time
        for u in [coord, cg_user]:
            for d in range(1, 6):
                base = day - timedelta(days=d)
                ci = base.replace(hour=8, minute=random.choice([0, 3, 7]))
                co = base.replace(hour=random.choice([16, 17]), minute=random.choice([0, 30]))
                TimeEntry.objects.create(user=u, clock_in=ci, clock_out=co)
        # one open (still clocked in) entry for the caregiver
        TimeEntry.objects.create(user=cg_user,
                                 clock_in=now.replace(hour=8, minute=5) if now.hour >= 9 else now - timedelta(hours=1))

        # --- Marketing / CRM demo leads ---
        from clients.models import Lead
        _leads = [
            ("Odette Mbayo", "PHONE", "Personnes âgées", "NEW", "Dr. Kalala"),
            ("Henri Tshibangu", "REFERRAL", "Mobilité réduite", "CONTACTED", "Hôpital Sendwe"),
            ("Claire Ilunga", "WEB", "Démence", "ASSESSMENT", ""),
            ("Joseph Kabeya", "HOSPITAL", "Post-opératoire", "ASSESSMENT", "Clinique Ngaliema"),
            ("Béatrice Mwamba", "REFERRAL", "Diabète", "NEW", "Famille"),
        ]
        for nm, src, need, stg, ref in _leads:
            Lead.objects.create(name=nm, source=src, care_need=need, stage=stg,
                                referred_by=ref, phone="+243 8XX XXX XXX")

        # --- Contracts + caregiver evaluations (Clients / Quality) ---
        from clients.models import ClientContract
        from caregivers.models import CaregiverEvaluation
        for cl in clients[:12]:
            ClientContract.objects.create(
                client=cl, reference=f"CTR-{cl.code.split('#')[-1]}",
                hours_per_week=random.choice([6, 9, 12, 15]), hourly_rate=cl.bill_rate,
                start_date=day.date() - timedelta(days=random.randint(30, 300)), status="ACTIVE")
        for cg in caregivers[:14]:
            CaregiverEvaluation.objects.create(
                caregiver=cg, period="T2 2026", evaluator=coord,
                punctuality=random.randint(3, 5), care_quality=random.randint(3, 5),
                communication=random.randint(3, 5), professionalism=random.randint(4, 5),
                notes=random.choice(["Très bon travail.", "Ponctualité à améliorer.", "Excellent relationnel.", ""]))

        # --- Client needs assessments (CLIENT -> ASSESSMENT -> CARE PLAN) ---
        from clients.models import ClientAssessment
        _adl = ["Hygiène", "Repas", "Médication", "Mobilité", "Toilette"]
        for cl in clients[:14]:
            ClientAssessment.objects.create(
                client=cl, assessed_on=day.date() - timedelta(days=random.randint(20, 200)),
                assessor=coord, mobility=random.choice(["INDEPENDENT", "ASSISTED", "DEPENDENT"]),
                cognition=random.choice(["NORMAL", "MILD", "MODERATE"]),
                fall_risk=random.choice(["LOW", "MEDIUM", "HIGH"]),
                adl_needs=", ".join(random.sample(_adl, random.randint(2, 4))),
                recommended_hours=random.choice([6, 9, 12, 15]),
                recommended_care_type=cl.care_type, status="COMPLETED")

        # --- Caregiver documents ---
        from caregivers.models import CaregiverDocument
        _docs = [("Carte d'identité", "ID"), ("Contrat de travail", "CONTRACT"),
                 ("Visite médicale", "MEDICAL"), ("Lettre de référence", "REFERENCE")]
        for cg in caregivers[:16]:
            for nm, ty in random.sample(_docs, random.randint(2, 4)):
                CaregiverDocument.objects.create(
                    caregiver=cg, name=nm, doc_type=ty,
                    status=random.choice(["VALID", "VALID", "VALID", "PENDING"]),
                    reference=f"DOC-{random.randint(1000,9999)}")

        # --- Assign login ID numbers + phones to all users ---
        for i, u in enumerate(User.objects.all().order_by("id"), 1):
            if not u.id_number:
                u.id_number = f"ID-{10000 + i}"
            if not u.phone:
                u.phone = f"+243 97{random.randint(1000000, 9999999)}"
            u.save(update_fields=["id_number", "phone"])

        # --- Agency settings singleton (control center) ---
        from accounts.models import AgencySettings
        AgencySettings.objects.all().delete()
        AgencySettings.objects.create()

        # --- Role-based access demo users ---
        coord.role = Role.MANAGER  # René = manager (full access)
        coord.save(update_fields=["role"])
        for uname, role, pwd in [("financier", Role.FINANCE, "finance123"),
                                 ("superviseur", Role.SUPERVISOR, "super123")]:
            u, _ = User.objects.get_or_create(
                username=uname, defaults={"email": f"{uname}@panthergroup.cd",
                                          "role": role, "id_number": f"ID-9{random.randint(1000,9999)}"})
            u.role = role
            u.set_password(pwd)
            u.save()

        self.stdout.write(self.style.SUCCESS(
            f"OK — {Client.objects.count()} clients, {Caregiver.objects.count()} soignants, "
            f"{Visit.objects.count()} visites."))
        self.stdout.write("Connexion coordinateur :  rene / panther123")
        self.stdout.write("Connexion soignant     :  soignant / soignant123")
        self.stdout.write("Connexion famille      :  famille / famille123")
