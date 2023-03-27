import io
import pytest
from rest_framework import serializers
from django.db import models
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


@ts_interface(context='choice')
class OtherSerializer(serializers.Serializer):
    field = serializers.IntegerField()


@ts_interface(context='annotations')
class OtherSerializer(serializers.Serializer):
    text_field = serializers.CharField(min_length=10, max_length=100, label='Huge Text Field')
    number_field = serializers.IntegerField(min_value=1, max_value=50)
    email_field = serializers.EmailField()
    date_field = serializers.DateField()
    datetime_field = serializers.DateTimeField()
    time_field = serializers.TimeField()
    uuid_field = serializers.UUIDField()
    url_field = serializers.URLField(default='https://google.com')
    float_field = serializers.FloatField()


class ActionType(models.TextChoices):
    ACTION1 = "Action1", ("Action1")
    ACTION2 = "Action2", ("Action2")
    ACTION3 = "Action3", ("Action3")


class NumberType(models.IntegerChoices):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@ts_interface('choices')
class ChoiceSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ActionType.choices)
    num = serializers.ChoiceField(choices=NumberType.choices)


@ts_interface('enumChoices')
class EnumChoiceSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ActionType.choices)
    num = serializers.ChoiceField(choices=NumberType.choices)


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


def test_choices():
    expected = """export interface ChoiceSerializer {
    action: "Action1" | "Action2" | "Action3";
    num: 1 | 2 | 3;
}

"""
    interfaces = get_ts('choices')
    assert interfaces == expected


def test_choices_enum():
    expected = """export enum ActionChoiceEnum {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum NumChoiceEnum {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnum;
    num: NumChoiceEnum;
}

"""
    interfaces = get_ts('enumChoices', enum_choices=True)
    assert interfaces == expected


def test_enum_values_with_enum_choices():
    expected = """export enum ActionChoiceEnum {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum ActionChoiceEnumValues {
    Action1 = 'Action1',
    Action2 = 'Action2',
    Action3 = 'Action3',
}

export enum NumChoiceEnum {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnum;
    num: NumChoiceEnum;
}

"""
    interfaces = get_ts('enumChoices', enum_choices=True, enum_values=True)
    assert interfaces == expected


def test_annotations():
    expected = """export interface OtherSerializer {
    /**
    * @label Huge Text Field
    * @minLength 10
    * @maxLength 100
    */
    text_field: string;
    /**
    * @minimum 1
    * @maximum 50
    */
    number_field: number;
    /**
    * @format email
    */
    email_field: string;
    /**
    * @format date
    */
    date_field: string;
    /**
    * @format date-time
    */
    datetime_field: string;
    /**
    * @format time
    */
    time_field: string;
    /**
    * @format uuid
    */
    uuid_field: string;
    /**
    * @default "https://google.com"
    * @format url
    */
    url_field?: string;
    /**
    * @format double
    */
    float_field: number;
}

"""
    interfaces = get_ts('annotations', annotations=True)
    assert interfaces == expected


def test_enum_values_without_enum_choices():
    expected = """export enum ActionChoiceEnumValues {
    Action1 = 'Action1',
    Action2 = 'Action2',
    Action3 = 'Action3',
}


export interface EnumChoiceSerializer {
    action: "Action1" | "Action2" | "Action3";
    num: 1 | 2 | 3;
}

"""
    interfaces = get_ts('enumChoices', enum_values=True, enum_choices=False)
    assert interfaces == expected
