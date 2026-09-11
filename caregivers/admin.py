from django.contrib import admin

from dashboard.admin_helpers import export_csv
from .models import Applicant, Availability, Caregiver, Certification, Skill


class CertInline(admin.TabularInline):
    model = Certification
    extra = 0


class AvailInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "reliability_score", "punctuality_score",
                    "weekly_hours_cap", "active")
    list_filter = ("active", "skills")
    search_fields = ("code", "first_name", "last_name")
    filter_horizontal = ("skills",)
    list_per_page = 25
    inlines = [CertInline, AvailInline]
    actions = [export_csv]


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "stage", "created_at")
    list_filter = ("stage",)
    search_fields = ("first_name", "last_name")
    date_hierarchy = "created_at"
    actions = [export_csv, "advance_stage"]

    @admin.action(description="Faire avancer d'une étape (recrutement)")
    def advance_stage(self, request, queryset):
        from .models import ApplicationStage
        order = [c[0] for c in ApplicationStage.choices]
        n = 0
        for a in queryset:
            i = order.index(a.stage)
            if i < len(order) - 1:
                a.stage = order[i + 1]; a.save(update_fields=["stage"]); n += 1
        self.message_user(request, f"{n} candidat(s) avancé(s) d'une étape.")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)


from .models import CaregiverEvaluation


@admin.register(CaregiverEvaluation)
class CaregiverEvaluationAdmin(admin.ModelAdmin):
    list_display = ("caregiver", "period", "score", "created_at")
    search_fields = ("caregiver__code", "period")
    autocomplete_fields = ("caregiver", "evaluator")


from .models import CaregiverDocument


@admin.register(CaregiverDocument)
class CaregiverDocumentAdmin(admin.ModelAdmin):
    list_display = ("caregiver", "name", "doc_type", "status", "expires_on")
    list_filter = ("doc_type", "status")
    search_fields = ("caregiver__code", "name")
    autocomplete_fields = ("caregiver",)
