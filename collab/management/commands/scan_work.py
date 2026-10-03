from django.core.management.base import BaseCommand
from collab.services import run_scan


class Command(BaseCommand):
    help = "Scan records and surface work items for the team."

    def handle(self, *a, **k):
        r = run_scan()
        self.stdout.write(self.style.SUCCESS(
            f"Scan OK — {r['created']} nouveaux, {r['updated']} maj, {r['auto_closed']} clotures."))
