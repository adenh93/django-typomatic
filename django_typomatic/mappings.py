from rest_framework import serializers


mappings = {
    serializers.BooleanField: 'boolean',
    serializers.NullBooleanField: 'boolean',
    serializers.CharField: 'string',
    serializers.EmailField: 'string',
    serializers.RegexField: 'string',
    serializers.SlugField: 'string',
    serializers.URLField: 'string',
    serializers.UUIDField: 'string',
    serializers.FilePathField: 'string',
    serializers.IPAddressField: 'string',
    serializers.IntegerField: 'number',
    serializers.FloatField: 'number',
    serializers.DecimalField: 'number',
    serializers.DateTimeField: 'Date',
    serializers.DateField: 'Date',
    serializers.TimeField: 'Date',
    serializers.DurationField: 'Date',
    serializers.DictField: 'Map'
}
