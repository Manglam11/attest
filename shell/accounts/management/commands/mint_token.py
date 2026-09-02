from django.core.management.base import BaseCommand

from accounts.tokens import mint_token


class Command(BaseCommand):
    help = "Mint a signed engine token for the given owner_id (testing/ops use)."

    def add_arguments(self, parser):
        parser.add_argument("owner_id")
        parser.add_argument("--ttl", type=int, default=None)

    def handle(self, *args, **options):
        kwargs = {}
        if options["ttl"] is not None:
            kwargs["ttl_seconds"] = options["ttl"]
        self.stdout.write(mint_token(options["owner_id"], **kwargs))
