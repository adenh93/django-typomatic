import inspect
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import sys

from django_typomatic import ts_interface, generate_ts
from rest_framework.serializers import BaseSerializer


class Command(BaseCommand):
    help = 'Generate TS types from serializer'

    @property
    def log_output(self):
        return self.stdout

    def log(self, msg):
        self.log_output.write(msg)

    def add_arguments(self, parser):
        parser.add_argument(
            '--serializers',
            '-s',
            help='Serializers enumeration '
                 'formats: module_name.SerializerName | module_name',
            nargs="*",
            type=str,
            default=[]
        )
        parser.add_argument(
            '--all',
            help='Generate TS types for all project serializers',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '--trim',
            '-t',
            help='Trim "serializer" from type name',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '--camelize',
            '-c',
            help='Camelize field names',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '--annotations',
            '-a',
            help='Add js doc annotations for validations (eg. for Zod)',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '--enum_choices',
            '-ec',
            help='Add choices to external enum type instead union',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '--enum_values',
            '-ev',
            help='Add enum for obtain display name for choices field',
            default=False,
            action='store_true'
        )
        parser.add_argument(
            '-o',
            '--output',
            help='Output folder for save TS files, by default save as ./types folder',
            default='./types'
        )

    @staticmethod
    def _get_app_serializers(app_name):
        serializers = []
        module = sys.modules.get(f'{app_name}.serializers', None)
        possibly_serializers = filter(lambda name: not name.startswith('_'), dir(module))

        for serializer_class_name in possibly_serializers:
            serializer_class = getattr(module, serializer_class_name)

            if not inspect.isclass(serializer_class):
                continue

            # Skip imported serializer classes
            if app_name not in serializer_class.__module__:
                continue

            if issubclass(serializer_class, BaseSerializer):
                serializers.append(f'{app_name}.{serializer_class.__name__}')

        return serializers

    def _generate_ts(self, app_name, serializer_name, output, **options):
        module = sys.modules.get(f'{app_name}.serializers', None)

        if not module:
            self.stdout.write(f'In app #{app_name} not found serializers file, skip', self.style.WARNING)
            return

        serializer_class = getattr(module, serializer_name)
        ts_interface(context=app_name)(serializer_class)

        output_path = Path(output) / app_name / 'index.ts'

        generate_ts(
            output_path,
            context=app_name,
            enum_values=options['enum_values'],
            enum_choices=options['enum_choices'],
            camelize=options['camelize'],
            trim_serializer_output=options['trim'],
            annotations=options['annotations']
        )
        self.stdout.write(f'[+] {app_name}.{serializer_name}')

    def handle(self, *args, serializers, output, all, **options):
        if all and serializers:
            raise CommandError('Only --all or --serializers must be specified, not together')

        if all:
            for app in apps.get_app_configs():
                # Filter external modules
                if str(settings.BASE_DIR) not in app.path:
                    continue

                serializers += self._get_app_serializers(app.name)

        for serializer in serializers:
            user_input = serializer.split('.')

            # Only app name
            if len(user_input) == 1:
                app_name = user_input[0]
                serializers_list = self._get_app_serializers(app_name)

                for s in serializers_list:
                    _, serializer_name = s.split('.')
                    self._generate_ts(app_name, serializer_name, output, **options)
            # App name with serializer e.g. user.UserSerializer
            elif len(user_input) == 2:
                app_name, serializer_name = user_input
                self._generate_ts(app_name, serializer_name, output, **options)
            else:
                self.stdout.write(f'Wrong format ({serializer})', self.style.ERROR)
