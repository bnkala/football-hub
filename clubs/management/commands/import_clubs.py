from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Import football clubs into Football Hub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--competition",
            type=str,
            required=True,
            help="Competition name"
        )

        parser.add_argument(
            "--season",
            type=str,
            required=True,
            help="Season name, e.g. 2026/27"
        )


    def handle(self, *args, **options):
        competition = options["competition"]
        season = options["season"]

        self.stdout.write(
            self.style.SUCCESS(f"Club importer initialized for {competition} - {season}")
        )