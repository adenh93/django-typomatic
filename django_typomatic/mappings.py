import django
from django.db.models import fields
from rest_framework import serializers
from packaging.version import Version

mappings = {
    fields.AutoField: 'number',
    fields.BigAutoField: 'number',
    fields.BigIntegerField : 'number',
    fields.BinaryField: 'string',
    fields.BooleanField: 'boolean',
    fields.CharField: 'string',
    fields.CommaSeparatedIntegerField: 'string',
    fields.DateField: 'string',
    fields.DateTimeField: 'string',
    fields.DecimalField: 'number',
    fields.DurationField: 'string',
    fields.EmailField: 'string',
    fields.FilePathField: 'string',
    fields.FloatField: 'number',
    fields.GenericIPAddressField: 'string',
    fields.IPAddressField: 'string',
    fields.IntegerField: 'number',
    fields.PositiveIntegerField: 'number',
    fields.PositiveSmallIntegerField: 'number',
    fields.SlugField: 'string',
    fields.SmallAutoField: 'number',
    fields.SmallIntegerField: 'number',
    fields.TextField: 'string',
    fields.TimeField: 'string',
    fields.URLField: 'string',
    fields.UUIDField: 'string',
    serializers.BooleanField: 'boolean',
    serializers.CharField: 'string',
    serializers.EmailField: 'string',
    serializers.RegexField: 'string',
    serializers.SlugField: 'string',
    serializers.URLField: 'string',
    serializers.DictField: 'string',
    serializers.UUIDField: 'string',
    serializers.FilePathField: 'string',
    serializers.FileField: 'File',
    serializers.ImageField: 'File',
    serializers.IPAddressField: 'string',
    serializers.IntegerField: 'number',
    serializers.FloatField: 'number',
    serializers.DecimalField: 'number',
    serializers.DateTimeField: 'string',
    serializers.DateField: 'string',
    serializers.TimeField: 'string',
    serializers.DurationField: 'string',
}

# PositiveBigIntegerField was added in Django 3.1
if Version(django.__version__) >= Version('3.1'):
    mappings[fields.PositiveBigIntegerField] = 'number'

format_mappings = {
    serializers.EmailField: 'email',
    serializers.URLField: 'url',
    serializers.UUIDField: 'uuid',
    serializers.DateTimeField: 'date-time',
    serializers.DateField: 'date',
    serializers.TimeField: 'time',
    serializers.FloatField: 'double',
}

primitives_mapping = {
    str: 'string',
    int: 'number',
    float: 'number',
    bool: 'boolean',
    dict: 'string',
    None: 'null'
}
