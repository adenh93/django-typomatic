import inspect
from importlib import import_module
from pathlib import Path
from typing import List

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import sys

from django_typomatic import ts_interface, generate_ts
from rest_framework.serializers import BaseSerializer


class Command(BaseCommand):
    help = "Generate TS types from serializer"

    @property
    def log_output(self):
        return self.stdout

    def log(self, msg):
        self.log_output.write(msg)

    def add_arguments(self, parser):
        parser.add_argument(
            "--serializers",
            "-s",
            help="Serializers enumeration" "formats: module_name.SerializerName",
            nargs="*",
            type=str,
            default=[],
        )
        parser.add_argument(
            "--app_name",
            help="Application to generate TS for" "formats: app_name",
            nargs=1,
            type=str,
            default=[],
        )
        parser.add_argument(
            "--all",
            help="Generate TS types for all project serializers",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--trim",
            "-t",
            help='Trim "serializer" from type name',
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--camelize",
            "-c",
            help="Camelize field names",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--annotations",
            "-a",
            help="Add js doc annotations for validations (eg. for Zod)",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--enum_choices",
            "-ec",
            help="Add choices to external enum type instead union",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--enum_values",
            "-ev",
            help="Add enum for obtain display name for choices field",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "--enum_keys",
            "-ek",
            help="Add enum keys by values for obtain display name for choices field",
            default=False,
            action="store_true",
        )
        parser.add_argument(
            "-o",
            "--output",
            help="Output folder for save TS files, by default save as ./types folder",
            default="./types",
        )

    def _get_app_serializers(self, module_name: str, level=0) -> List[str]:
        serializers = []
        module = None
        try:
            if "rest_framework" not in module_name:
                module = import_module(module_name)
        except ModuleNotFoundError:
            pass

        if module:
            possibly = filter(lambda name: not name.startswith("_"), dir(module))
        else:
            possibly = []

        for field_name in possibly:
            field = getattr(module, field_name)

            if inspect.ismodule(field):
                if module_name in field.__name__:
                    serializers.extend(
                        self._get_app_serializers(
                            f"{module_name}.{field_name}", level + 1
                        )
                    )

            if inspect.isclass(field):
                if module_name in field.__module__ and issubclass(
                    field, BaseSerializer
                ):
                    serializers.append(f"{module_name}.{field_name}")

        return serializers

    def _generate_ts(self, module_name, serializer_name, output, **options):
        module = None
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            pass

        if not module:
            self.stdout.write(
                f"Module {module_name} not found, skip", self.style.WARNING
            )
            return

        serializer_class = getattr(module, serializer_name)
        ts_interface(context=module_name)(serializer_class)

        output_path = Path(output) / module_name / "index.ts"

        generate_ts(
            output_path,
            context=module_name,
            enum_choices=options["enum_choices"],
            enum_values=options["enum_values"],
            enum_keys=options["enum_keys"],
            camelize=options["camelize"],
            trim_serializer_output=options["trim"],
            annotations=options["annotations"],
        )
        self.stdout.write(f"[+] {module_name}.{serializer_name}")

    def handle(self, *args, serializers, app_name, output, all, **options):
        if sum([bool(serializers), bool(app_name), bool(all)]) != 1:
            raise CommandError(
                "Only one of --all, --app_name or --serializers must be specified"
            )

        if all:
            for app in apps.get_app_configs():
                # Include only modules defined within this django project's
                # directory
                if Path(settings.BASE_DIR) not in Path(app.path).parents:
                    continue

                serializers += self._get_app_serializers(app.name)

        if app_name:
            serializers = self._get_app_serializers(app_name[0])

        for serializer in serializers:
            module_name, serializer_name = serializer.rsplit(".", 1)
            self._generate_ts(module_name, serializer_name, output, **options)
