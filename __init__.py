from rest_framework import serializers
from typomatic import generate_ts, ts_interface


@ts_interface()
class Foo(serializers.Serializer):
    foo = serializers.CharField()
    bar = serializers.IntegerField()


@ts_interface()
class Bar(serializers.Serializer):
    foo = Foo()
    foo_many = Foo(many=True)
    bar = serializers.ListField(
        child=serializers.IntegerField()
    )
    date = serializers.DateTimeField()


generate_ts('./output.ts')