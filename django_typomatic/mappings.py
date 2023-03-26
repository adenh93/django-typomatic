from rest_framework import serializers

mappings = {
    serializers.BooleanField: 'boolean',
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
    serializers.DateTimeField: 'string',
    serializers.DateField: 'string',
    serializers.TimeField: 'string',
    serializers.DurationField: 'string',
    serializers.DictField: 'Map'
}

format_mappings = {
    serializers.EmailField: 'email',
    serializers.URLField: 'url',
    serializers.UUIDField: 'uuid',
    serializers.DateTimeField: 'date-time',
    serializers.DateField: 'date',
    serializers.TimeField: 'time',
    serializers.FloatField: 'double',
}
