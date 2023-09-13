from django.apps import AppConfig


class AppNameConfig(AppConfig):
    '''
    Set app name for running the tests with Models
    '''
    name = 'management'
    verbose_name = 'Django Typomatic'
