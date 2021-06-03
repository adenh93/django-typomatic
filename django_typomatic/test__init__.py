import io
import pytest
from rest_framework import serializers
from unittest.mock import patch, mock_open, MagicMock
from . import ts_interface, generate_ts, get_ts


@ts_interface(context='internal')
class FooSerializer(serializers.Serializer):
    some_field = serializers.ListField(child=serializers.IntegerField())
    another_field = serializers.CharField()
    null_field = serializers.CharField(allow_null=True)


@ts_interface(context='internal')
class BarSerializer(serializers.Serializer):
    foo = FooSerializer()
    foos = FooSerializer(many=True)
    bar_field = serializers.CharField()


@ts_interface(context='external')
class OtherSerializer(serializers.Serializer):
    field = serializers.IntegerField()


def test_get_ts():
    expected = """export interface FooSerializer {
    some_field: number[];
    another_field: string;
    null_field: string | null;
}

export interface BarSerializer {
    foo: FooSerializer;
    foos: FooSerializer[];
    bar_field: string;
}

"""
    interfaces = get_ts('internal')
    assert interfaces == expected


def test_exclude_serializer():
    expected = """export interface Foo {
    some_field: number[];
    another_field: string;
    null_field: string | null;
}

export interface Bar {
    foo: Foo;
    foos: Foo[];
    bar_field: string;
}

"""
    interfaces = get_ts('internal', trim_serializer_output=True)
    assert interfaces == expected

def test_camlize():
    expected = """export interface FooSerializer {
    someField: number[];
    anotherField: string;
    nullField: string | null;
}

export interface BarSerializer {
    foo: FooSerializer;
    foos: FooSerializer[];
    barField: string;
}

"""
    interfaces = get_ts('internal', camelize=True)
    assert interfaces == expected

