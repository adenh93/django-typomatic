import logging
from pathlib import Path

from rest_framework import serializers
from rest_framework.serializers import BaseSerializer
from rest_framework.fields import empty

from django.db.models import OneToOneField
from django.db.models.enums import Choices
import inspect

from typing import get_type_hints, get_origin, get_args

from .mappings import mappings, format_mappings, primitives_mapping

_LOG = logging.getLogger(f"django-typomatic.{__name__}")

# Serializers
__serializers = dict()
# Custom serializers.Field to TS Type mappings
__field_mappings = dict()
# Custom field_name to TS Type overrides
__mapping_overrides = dict()
# TS Type imports import
__imports = dict()


def ts_field(ts_type: str, context='default'):
    '''
    Any valid Django Rest Framework Serializer Field with this class decorator will
    be added to a list in a __field_mappings dictionary.
    Useful to define the type mapping of custom serializer Fields.
    e.g.
    @ts_field('string')
    class CustomFieldField(serializers.Field):
        def to_internal_value(self, data):
            pass
        def to_representation(self, obj):
            pass
    '''

    def decorator(cls):
        if issubclass(cls, serializers.Field):
            if context not in __field_mappings:
                __field_mappings[context] = dict()
            if cls not in __field_mappings[context]:
                __field_mappings[context][cls] = ts_type
        return cls

    return decorator


def ts_interface(context='default', mapping_overrides=None):
    '''
    Any valid Django Rest Framework Serializers with this class decorator will
    be added to a list in a dictionary.
    Optional parameters:
    'context': Will create separate dictionary keys per context.
        Otherwise, all values will be inserted into a list with a key of 'default'.
    'mapping_overrides': Dictionary of field_names to TS types
        Useful to properly serialize ModelSerializer runtime properties and ReadOnlyFields.
    e.g.
    @ts_interface(context='internal', mapping_overrides={"baz" : "string[]"})
    class Foo(serializers.Serializer):
        bar = serializer.IntegerField()
        baz = serializer.ReadOnlyField(source='baz_property')
    '''

    def decorator(cls):
        if issubclass(cls, serializers.Serializer):
            if context not in __field_mappings:
                __field_mappings[context] = dict()
            if context not in __serializers:
                __serializers[context] = []
            __serializers[context].append(cls)
            if mapping_overrides:
                if context not in __mapping_overrides:
                    __mapping_overrides[context] = dict()
                if cls not in __mapping_overrides[context]:
                    __mapping_overrides[context][cls] = mapping_overrides
        return cls

    return decorator


def ts_format(format):
    def decorator(f):
        f.format = format
        return f

    return decorator


def __get_trimmed_name(name, trim_serializer_output):
    key = "Serializer"
    return name[:-len(key)] if trim_serializer_output and name.endswith(key) else name


def __map_choices_to_union(field_name, choices):
    '''
    Generates and returns a TS union type for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Choice Field: {field_name}')
        return 'any'

    return ' | '.join(f'"{key}"' if type(key) == str else str(key) for key in choices.keys())


def __get_choices_escape_spec_chars(choices):
    '''
    Get booleans whether the keys and/or values of a choices field have special characters
    :param choices: choices field to check
    :return: whether the keys and values should be formatted as a string in the enum
    '''
    spec_chars = {'~', ':', '+', '[', '\\', '@', '^', '{', '%', '(', '-', '"', '*', '|', ',', '&',
                  '<', '`', '}', '.', '=', ']', '!', '>', ';', '?', '#', '$', ')', '/'}
    key_string = any(type(key) == str and (char in key or key[0].isdigit())
                     for char in spec_chars for key in choices.keys())
    value_string = any(type(value) == str and (char in value or value[0].isdigit())
                       for char in spec_chars for value in choices.values())
    return key_string, value_string


def __map_choices_to_enum(enum_name, choices):
    '''
    Generates and returns a TS enum for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Enum Field: {enum_name}')
        return f'let {enum_name} = any;'

    choices_enum = f"export enum {enum_name} {{\n"
    key_esc, value_esc = __get_choices_escape_spec_chars(choices)
    for key, value in choices.items():
        if type(value) == str:
            value = value.replace("'", "\\'")
        if type(key) == str:
            key = key.replace("'", "\\'")
        if type(key) == str and key_esc:
            choices_enum = choices_enum + f"    '{str(key).upper().replace(' ', '_')}' = '{key}',\n"
        elif type(key) == str and not key_esc:
            choices_enum = choices_enum + f"    {str(key).upper().replace(' ', '_')} = '{key}',\n"
        elif value_esc and key_esc and type(key) == str:
            choices_enum = choices_enum + f"    '{str(value).upper().replace(' ', '_')}' = '{key}',\n"
        elif value_esc:
            choices_enum = choices_enum + f"    '{str(value).upper().replace(' ', '_')}' = {key},\n"
        else:
            choices_enum = choices_enum + f"    {str(value).upper().replace(' ', '_')} = {key},\n"
    choices_enum = choices_enum + "}\n"

    return choices_enum


def __map_choices_to_enum_values(enum_name, choices):
    '''
    Generates and returns a TS enum values (display name) for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Enum Field: {enum_name}')
        return f'let {enum_name} = any;'

    choices_enum = f"export enum {enum_name} {{\n"
    key_esc, _ = __get_choices_escape_spec_chars(choices)
    for key, value in choices.items():
        if type(value) == str:
            value = value.replace("'", "\\'")
        if type(key) == str:
            key = key.replace("'", "\'")
        if type(key) == str and key_esc:
            choices_enum = choices_enum + f"    '{str(key).replace(' ', '_')}' = '{value}',\n"
        elif type(key) == str:
            choices_enum = choices_enum + f"    {str(key).replace(' ', '_')} = '{value}',\n"
        else:
            print("Number enums not need it")
            return None
    choices_enum = choices_enum + "}\n"

    return choices_enum


def __map_choices_to_enum_keys_by_values(enum_name, choices):
    '''
    Generates and returns a TS enum values (display name) for all keys by the values in the
    provided choices OrderedDict. Format as follows:
     "export enum FieldNameChoiceEnumKeys { VALUE1 = 'key1', VALUE2 = 'key2' }"
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Enum Field: {enum_name}')
        return f'let {enum_name} = any;'

    choices_enum = f"export enum {enum_name} {{\n"
    _, value_esc = __get_choices_escape_spec_chars(choices)
    for key, value in choices.items():
        if type(value) == str:
            value = value.replace("'", "\\'")
        if type(key) == str:
            key = key.replace("'", "\\'")
        if type(key) == str and value_esc:
            choices_enum = choices_enum + f"    '{str(value).upper().replace(' ', '_')}' = '{key}',\n"
        elif value_esc:
            choices_enum = choices_enum + f"    '{str(value).upper().replace(' ', '_')}' = {key},\n"
        elif type(key) == str:
            choices_enum = choices_enum + f"    {str(value).upper().replace(' ', '_')} = '{key}',\n"
        else:
            choices_enum = choices_enum + f"    {str(value).upper().replace(' ', '_')} = {key},\n"
    choices_enum = choices_enum + "}\n"

    return choices_enum


def __is_known_serializer_type(serializer_type, context):
    for _context, serializers in __serializers.items():
        if serializer_type in serializers:
            imports = __imports.get(context, {})
            type_imports = imports.get(_context, set())
            type_imports.add(serializer_type)
            imports[_context] = type_imports
            __imports[context] = imports
            return True
    return False


def __process_field(field_name, field, context, serializer, trim_serializer_output, camelize,
                    enum_choices, enum_values, enum_keys):
    '''
    Generates and returns a tuple representing the Typescript field name and Type.
    '''
    # For PrimaryKeyRelatedField, set field_type to the type of the primary key
    # on the related model
    if isinstance(field, serializers.PrimaryKeyRelatedField) and field.queryset:
        is_many = False

        target_field = field.queryset.model._meta.pk
        while isinstance(target_field, OneToOneField):
            # Recurse into the parent model the field is inheriting from
            target_field = target_field.model._meta.pk.target_field

        field_type = type(target_field)
    elif hasattr(field, 'child'):
        is_many = True
        field_type = type(field.child)
    elif hasattr(field, 'child_relation'):
        is_many = True
        field_type = type(field.child_relation)
    else:
        is_many = False
        field_type = type(field)

    if field_type in __serializers[context] or __is_known_serializer_type(field_type, context):
        ts_type = __get_trimmed_name(
            field_type.__name__, trim_serializer_output)
    elif field_type in __field_mappings[context]:
        ts_type = __field_mappings[context].get(field_type, 'any')
    elif (context in __mapping_overrides) and (serializer in __mapping_overrides[context]) \
            and field_name in __mapping_overrides[context][serializer]:
        ts_type = __mapping_overrides[context][serializer].get(
            field_name, 'any')
    elif field_type == serializers.PrimaryKeyRelatedField:
        ts_type = "number"
    elif hasattr(field, 'choice_strings_to_values') and enum_choices:
        ts_type = f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnum"
    elif hasattr(field, 'choice_strings_to_values') and enum_choices and enum_values \
            and not enum_keys:
        ts_type = f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnumValues"
    elif hasattr(field, 'choice_strings_to_values') and enum_keys:
        ts_type = f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnumKeys"
    elif hasattr(field, 'choice_strings_to_values'):
        ts_type = __map_choices_to_union(field_name, field.choices)
    elif field_type == serializers.SerializerMethodField:
        is_many, ts_type = __get_nested_serializer_field(context, enum_choices, enum_values,
                                                         enum_keys, field, field_name, is_many,
                                                         serializer, trim_serializer_output)
    else:
        ts_type = mappings.get(field_type, 'any')
    if is_many:
        ts_type += '[]'

    if camelize:
        field_name_components = field_name.split("_")
        field_name = field_name_components[0] + "".join(
            x.title() for x in field_name_components[1:])

    return field_name, ts_type


def __get_nested_serializer_field(context, enum_choices, enum_values, enum_keys, field, field_name,
                                  is_many, serializer, trim_serializer_output):
    types = []
    if field.method_name:
        field_function = getattr(serializer, field.method_name)
    else:
        field_function = getattr(serializer, f'get_{field_name}')
    return_type = get_type_hints(field_function).get('return')
    is_generic_type = hasattr(return_type, '__origin__')
    is_serializer_type = False
    many = False
    # TODO type pass recursively to represent something like a list from a list e.g. List[List[int]]
    if is_generic_type:
        return_type, many = __process_generic_type(return_type)
    if isinstance(return_type, list) or isinstance(return_type, tuple) or isinstance(
            return_type, set):
        return_types = return_type

        for return_type in return_types:
            many = False
            is_generic_type = hasattr(return_type, '__origin__')

            if is_generic_type:
                return_type, many = __process_generic_type(return_type)

            ts_type = __process_method_field(
                field_name, return_type, enum_choices, enum_values, enum_keys, many
            )
            types.append(ts_type)
    elif return_type:
        ts_type = __process_method_field(
            field_name, return_type, enum_choices, enum_values, enum_keys, many
        )

        if isinstance(return_type, BaseSerializer):
            many = return_type.many
            return_type = return_type.child.__class__

        if issubclass(return_type, BaseSerializer):
            is_external_serializer = return_type.__module__.replace('.serializers',
                                                                    '') != context
            is_serializer_type = True

            if is_external_serializer and return_type not in __serializers.get(context, []):
                # Import the serializer if it was previously generated
                if not __is_known_serializer_type(return_type, context):
                    # Include external Interface
                    ts_interface(context=context)(return_type)
                    # For duplicate interface, set not exported
                    setattr(return_type, '__exported__', False)

        if is_serializer_type:
            ts_type = __get_trimmed_name(return_type.__name__, trim_serializer_output)
            is_many = many

        types.append(ts_type)
    else:
        ts_type = __process_method_field(
            field_name, return_type, enum_choices, enum_values, enum_keys, many
        )
        types.append(ts_type)
    if hasattr(field_function, 'format'):
        field.format = field_function.format
    # Clear duplicate types
    types = list(dict.fromkeys(types))
    ts_type = " | ".join(types)
    return is_many, ts_type


def __process_generic_type(return_type):
    origin = get_origin(return_type)
    args = get_args(return_type)
    is_many = False

    if origin == list or origin == tuple or origin == set:
        is_many = True
        return_type = args[0]
    return return_type, is_many


def __process_choice_field(field_name, choices, enum_choices, enum_values, enum_keys):
    '''
    Get the typescript enums of a Choices field
    :param field_name: name of the Choices field
    :param choices: possibilities of the Choices field
    :param enum_choices: whether the regular choice enum should be returned
    :param enum_values: whether the values choice enum should be returned
    :param enum_keys:  whether the keys choice enum should be returned
    :return: strings of all the extracted typescript enums
    '''
    ts_enum = None
    ts_enum_value = None
    ts_enum_key = None

    ts_type = f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnum"
    if enum_choices:
        ts_enum = __map_choices_to_enum(ts_type, choices)
    if enum_values:
        ts_enum_value = __map_choices_to_enum_values(f'{ts_type}Values', choices)
    if enum_keys:
        ts_enum_key = __map_choices_to_enum_keys_by_values(f'{ts_type}Keys', choices)

    return ts_enum, ts_enum_value, ts_enum_key


def __process_method_field(field_name, return_type, enum_choices, enum_values, enum_keys, many=False):
    '''
    Function to set the typescript mapping for a Django Method Field
    '''
    if inspect.isclass(return_type) and issubclass(return_type, Choices):
        choices = {key: value for key, value in return_type.choices}

        if enum_choices:
            if enum_values:
                return f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnumValues"
            return f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnum"
        elif enum_keys:
            return f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnumKeys"
        else:
            return __map_choices_to_union(field_name, choices)

    ts_type = primitives_mapping.get(return_type, 'any')
    ts_type = ts_type if not many else f'{ts_type}[]'

    return ts_type


def __get_ts_interface(serializer, context, trim_serializer_output, camelize, enum_choices,
                       enum_values, enum_keys, annotations):
    '''
    Generates and returns a Typescript Interface by iterating
    through the serializer fields of the DRF Serializer class
    passed in as a parameter, and mapping them to the appropriate Typescript
    data type.
    '''
    name = __get_trimmed_name(serializer.__name__, trim_serializer_output)
    _LOG.debug(f"Creating interface for {name}")
    fields = []
    if hasattr(serializer, 'get_fields') and hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'model'):
        instance = serializer()
        fields = instance.get_fields().items()
    else:
        fields = serializer._declared_fields.items()
    ts_fields = []
    for key, value in fields:
        ts_property, ts_type = __process_field(key, value, context, serializer,
                                               trim_serializer_output, camelize, enum_choices,
                                               enum_values, enum_keys)

        if value.read_only or not value.required:
            ts_property = ts_property + "?"

        if value.allow_null:
            ts_type = ts_type + " | null"

        if annotations:
            annotations_list = __get_annotations(value, ts_type)
            if annotations_list:
                ts_fields.append('\n'.join(annotations_list))

        ts_fields.append(f"    {ts_property}: {ts_type};")
    collapsed_fields = '\n'.join(ts_fields)
    exported = getattr(serializer, '__exported__', True)
    return f'{"export " if exported else ""}interface {name} {{\n{collapsed_fields}\n}}\n\n'


def __generate_imports(context, trim_serializer_output):
    imports_str = ''
    if context in __imports:
        for package, serializers in __imports[context].items():
            names = []
            for serializer in serializers:
                name = __get_trimmed_name(
                    serializer.__name__, trim_serializer_output)
                names.append(name)

            imports_str += "import type { %s } from '../%s';\n" % (
                ', '.join(names), package)
        imports_str += '\n'
    return imports_str


def __generate_interfaces(context, trim_serializer_output, camelize, enum_choices, enum_values,
                          enum_keys, annotations):
    if context not in __serializers:
        return []
    return [__get_ts_interface(serializer, context, trim_serializer_output, camelize,
                               enum_choices, enum_values, enum_keys, annotations) for serializer in
            __serializers[context]]


def __generate_enums(context, enum_choices, enum_values, enum_keys):
    '''
    Function to generate a string of all the possible enums (including possible duplicates). This
    does not change the mapping of the interfaces but only generates enums from used choice fields.
    '''
    enums = []
    if context not in __serializers:
        return []
    for serializer in __serializers[context]:
        if hasattr(serializer, 'get_fields'):
            instance = serializer()
            fields = instance.get_fields().items()
        else:
            fields = serializer._declared_fields.items()
        for field_name, field in fields:
            ts_enum, ts_enum_value, ts_enum_key = __extract_field_enums(
                enum_choices, enum_values, enum_keys, field, field_name, serializer)

            if ts_enum_value is not None:
                enums.append(ts_enum_value)
            if ts_enum_key is not None:
                enums.append(ts_enum_key)
            if ts_enum is not None:
                enums.append(ts_enum)

    return enums


def __extract_field_enums(enum_choices, enum_values, enum_keys, field, field_name, serializer):
    ts_enum, ts_enum_value, ts_enum_key = None, None, None
    if hasattr(field, 'choice_strings_to_values'):
        ts_enum, ts_enum_value, ts_enum_key = __process_choice_field(
            field_name, field.choices, enum_choices, enum_values, enum_keys,
        )
    if hasattr(field, 'child'):
        field_type = type(field.child)
    elif hasattr(field, 'child_relation'):
        field_type = type(field.child_relation)
    else:
        field_type = type(field)
    if field_type == serializers.SerializerMethodField:
        field_function = getattr(serializer, f'get_{field_name}')
        return_type = get_type_hints(field_function).get('return')
        if inspect.isclass(return_type) and issubclass(return_type, Choices):
            choices = {key: value for key, value in return_type.choices}
            ts_enum, ts_enum_value, ts_enum_key = __process_choice_field(
                field_name, choices, enum_choices, enum_values, enum_keys
            )
    return ts_enum, ts_enum_value, ts_enum_key


def __remove_duplicate_enums(enums):
    '''
    The enums are compared such that there are no duplicates between interfaces. Then the enums are
    returned in string format with blank lines in between.
    '''
    enums_string = ''
    if any(elem is not None for elem in enums):
        distinct_enums = sorted(list(set(list(filter(lambda x: x is not None, enums)))))
        enums_string = '\n'.join(distinct_enums) + '\n\n'
    return enums_string


def __get_annotations(field, ts_type):
    annotations = ['    /**']
    if field.label:
        annotations.append(f'    * @label {field.label}')

    default = field.default if field.default != empty else None

    if 'string' in ts_type:
        if getattr(field, 'min_length', None):
            annotations.append(f'    * @minLength {field.min_length}')
        if getattr(field, 'max_length', None):
            annotations.append(f'    * @maxLength {field.max_length}')

        if default is not None and 'number | string' not in ts_type:
            annotations.append(f'    * @default "{default}"')

    if 'number' in ts_type:
        if getattr(field, 'min_value', None):
            annotations.append(f'    * @minimum {field.min_value}')
        if getattr(field, 'max_value', None):
            annotations.append(f'    * @maximum {field.max_value}')

        if default is not None:
            annotations.append(f'    * @default {default}')

    field_type = type(field)

    if field_type in format_mappings:
        annotations.append(f'    * @format {format_mappings[field_type]}')
    elif hasattr(field, 'format'):
        annotations.append(f'    * @format {field.format}')

    annotations.append('    */')

    # Clear annotations header and footer if nothing to include
    if len(annotations) == 2:
        annotations = []

    return annotations


def generate_ts(output_path, context='default', trim_serializer_output=False, camelize=False,
                enum_choices=False, enum_values=False, enum_keys=False, annotations=False):
    '''
    When this function is called, a Typescript interface will be generated
    for each DRF Serializer in the serializers dictionary, depending on the
    optional context parameter provided. If the parameter is ignored, all
    serializers in the default value, 'default' will be iterated over and a
    list of Typescript interfaces will be returned via a list comprehension.

    The Typescript interfaces will then be outputted to the file provided.
    '''

    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True, parents=True)

    with open(output_path, 'w') as output_file:
        interfaces = __generate_interfaces(context, trim_serializer_output, camelize, enum_choices,
                                           enum_values, enum_keys, annotations)
        enums = []
        if enum_choices or enum_values or enum_keys:
            enums = __generate_enums(context, enum_choices, enum_values, enum_keys)
        enums_string = __remove_duplicate_enums(enums)
        imports = __generate_imports(context, trim_serializer_output)
        output_file.write(imports + enums_string + ''.join(interfaces))


def get_ts(context='default', trim_serializer_output=False, camelize=False, enum_choices=False,
           enum_values=False, enum_keys=False, annotations=False):
    '''
    Similar to generate_ts. But rather than outputting the generated
    interfaces to the specified file, will return the generated interfaces
    as a raw string.
    '''
    interfaces = __generate_interfaces(context, trim_serializer_output, camelize, enum_choices,
                                       enum_values, enum_keys, annotations)
    enums = []
    if enum_choices or enum_values or enum_keys:
        enums = __generate_enums(context, enum_choices, enum_values, enum_keys)
    enums_string = __remove_duplicate_enums(enums)
    return enums_string + ''.join(interfaces)
