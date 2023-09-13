import random
from typing import List

from rest_framework import serializers
from django.db import models
from . import ts_interface, get_ts, ts_format

from django.conf import settings
import django

settings.configure()
django.setup()

from django_typomatic.management.models import Album


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
    empty_annotation = serializers.CharField()
    custom_format = serializers.SerializerMethodField()

    @ts_format('email')
    def get_custom_format(self, instance) -> str:
        return 'test@email.com'


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


@ts_interface('files')
class FileSerializer(serializers.Serializer):
    image = serializers.ImageField()
    file = serializers.FileField()


@ts_interface('methodFields')
class MethodFieldsNestedSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=15)
    description = serializers.CharField(max_length=100)


@ts_interface('methodFields')
class MethodFieldsSerializer(serializers.Serializer):
    integer_field = serializers.SerializerMethodField()
    string_field = serializers.SerializerMethodField()
    float_field = serializers.SerializerMethodField()
    choice_field = serializers.SerializerMethodField()
    multiple_return = serializers.SerializerMethodField()
    various_type_return = serializers.SerializerMethodField()
    serializer_type_return = serializers.SerializerMethodField()

    def get_integer_field(self) -> int:
        return 5

    def get_string_field(self) -> str:
        return 'test'

    def get_float_field(self) -> float:
        return 1.1

    def get_choice_field(self) -> ActionType:
        return ActionType.ACTION1

    def get_multiple_return(self) -> List[int]:
        return [1, 2]

    def get_various_type_return(self) -> [int, str]:
        return random.choice([1, 'test'])

    def get_serializer_type_return(self) -> MethodFieldsNestedSerializer:
        return MethodFieldsNestedSerializer(name='test', description='Test')


@ts_interface('nestedEnums')
class AlbumSerializer(serializers.ModelSerializer):
    tracks = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='title'
    )
    num = serializers.ChoiceField(choices=NumberType.choices)

    class Meta:
        model = Album
        fields = '__all__'


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


def test_enum_keys_with_enum_choices():
    expected = """export enum ActionChoiceEnum {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum ActionChoiceEnumKeys {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum NumChoiceEnum {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}

export enum NumChoiceEnumKeys {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnum;
    num: NumChoiceEnum;
}

"""
    interfaces = get_ts('enumChoices', enum_choices=True, enum_keys=True)
    assert interfaces == expected


def test_enum_keys_without_enum_choices():
    expected = """export enum ActionChoiceEnumKeys {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum NumChoiceEnumKeys {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnumKeys;
    num: NumChoiceEnumKeys;
}

"""
    interfaces = get_ts('enumChoices', enum_keys=True, enum_choices=False)
    assert interfaces == expected


def test_enum_keys_and_values_with_enum_choices():
    expected = """export enum ActionChoiceEnum {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum ActionChoiceEnumKeys {
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

export enum NumChoiceEnumKeys {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnum;
    num: NumChoiceEnum;
}

"""
    interfaces = get_ts('enumChoices', enum_choices=True, enum_keys=True, enum_values=True)
    assert interfaces == expected


def test_enum_keys_and_values_without_enum_choices():
    expected = """export enum ActionChoiceEnumKeys {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}

export enum ActionChoiceEnumValues {
    Action1 = 'Action1',
    Action2 = 'Action2',
    Action3 = 'Action3',
}

export enum NumChoiceEnumKeys {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}


export interface EnumChoiceSerializer {
    action: ActionChoiceEnumKeys;
    num: NumChoiceEnumKeys;
}

"""
    interfaces = get_ts('enumChoices', enum_choices=False, enum_keys=True, enum_values=True)
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
    empty_annotation: string;
    /**
    * @format email
    */
    custom_format?: string;
}

"""
    interfaces = get_ts('annotations', annotations=True)
    assert interfaces == expected


def test_file_serializer():
    expected = """export interface FileSerializer {
    image: File;
    file: File;
}

"""
    interfaces = get_ts('files')
    assert interfaces == expected


def test_method_fields_serializer():
    expected = """export enum ChoiceFieldChoiceEnum {
    ACTION1 = 'Action1',
    ACTION2 = 'Action2',
    ACTION3 = 'Action3',
}


export interface MethodFieldsNestedSerializer {
    name: string;
    description: string;
}

export interface MethodFieldsSerializer {
    integer_field?: number;
    string_field?: string;
    float_field?: number;
    choice_field?: ChoiceFieldChoiceEnum;
    multiple_return?: number[];
    various_type_return?: number | string;
    serializer_type_return?: MethodFieldsNestedSerializer;
}

"""
    interfaces = get_ts('methodFields', enum_choices=True)
    assert interfaces == expected


def test_foreign_key_serializer_with_enums():
    expected = """export enum NumChoiceEnum {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}

export enum NumChoiceEnumKeys {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
}

export enum StatusChoiceEnum {
    '1' = '1',
    '2' = '2',
    '3' = '3',
    '4' = '4',
    '5' = '5',
    '6' = '6',
}

export enum StatusChoiceEnumKeys {
    'ARCHIVED' = '1',
    'PRE-SAVED' = '2',
    'SAVED' = '3',
    'USER\\'S_LIKES' = '4',
    'USER\\'S_DISLIKES' = '5',
    'NONE' = '6',
}

export enum StatusChoiceEnumValues {
    '1' = 'Archived',
    '2' = 'Pre-saved',
    '3' = 'Saved',
    '4' = 'User\\'s likes',
    '5' = 'User\\'s dislikes',
    '6' = 'None',
}


export interface AlbumSerializer {
    id?: number;
    tracks?: any[];
    num: NumChoiceEnum;
    album_name: string;
    artist: string;
    status: StatusChoiceEnum;
}

"""
    interfaces = get_ts('nestedEnums', enum_choices=True, enum_keys=True, enum_values=True)
    assert interfaces == expected
