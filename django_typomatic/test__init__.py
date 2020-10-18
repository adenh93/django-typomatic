import io
import pytest
from rest_framework import serializers
from unittest.mock import patch, mock_open, MagicMock
from . import ts_interface, generate_ts, get_ts


@ts_interface(context='internal')
class Foo(serializers.Serializer):
    some_field = serializers.ListField(child=serializers.IntegerField())
    another_field = serializers.CharField()


@ts_interface(context='internal')
class Bar(serializers.Serializer):
    foo = Foo()
    foos = Foo(many=True)
    bar_field = serializers.CharField()


@ts_interface(context='external')
class Other(serializers.Serializer):
    field = serializers.IntegerField()


expected = """export interface Foo {
    some_field: number[];
    another_field: string;
}

export interface Bar {
    foo: Foo;
    foos: Foo[];
    bar_field: string;
}

"""


def test_get_ts():
    interfaces = get_ts('internal')
    assert interfaces == expected
