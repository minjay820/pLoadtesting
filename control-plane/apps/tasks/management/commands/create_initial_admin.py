import getpass
import stat
from pathlib import Path

from django.contrib.auth import get_user_model, password_validation
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the first pLoadtesting admin account when no superuser exists."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username for the first admin account.")
        parser.add_argument("--email", default="", help="Optional email address for the admin account.")
        parser.add_argument(
            "--password-file",
            help="Path to a private file containing the admin password. On POSIX, mode must not allow group/other access.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip()
        password_file = options.get("password_file")

        if not username:
            raise CommandError("--username must not be blank.")

        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("Initial admin already exists; refusing to create or overwrite an admin account.")
        if User.objects.filter(**{User.USERNAME_FIELD: username}).exists():
            raise CommandError("A user with this username already exists; refusing to promote or overwrite it.")

        password = self._read_password(password_file)
        password_validation.validate_password(password)

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created initial admin user '{username}'."))

    def _read_password(self, password_file: str | None) -> str:
        if password_file:
            path = Path(password_file)
            try:
                file_stat = path.stat()
            except FileNotFoundError as exc:
                raise CommandError("Password file does not exist.") from exc

            if file_stat.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise CommandError("Password file must not be readable, writable, or executable by group/other users.")

            lines = path.read_text(encoding="utf-8").splitlines()
            password = lines[0].strip() if lines else ""
        else:
            password = getpass.getpass("Password: ").strip()
            password_confirm = getpass.getpass("Password (again): ").strip()
            if password != password_confirm:
                raise CommandError("Passwords do not match.")

        if not password:
            raise CommandError("Password must not be blank.")
        return password
