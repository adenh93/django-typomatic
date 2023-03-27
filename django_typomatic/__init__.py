import logging
from pathlib import Path

from .mappings import mappings

from rest_framework import serializers
from rest_framework.fields import empty

from .mappings import mappings, format_mappings

_LOG = logging.getLogger(f"django-typomatic.{__name__}")

# Serializers
__serializers = dict()
# Custom serializers.Field to TS Type mappings
__field_mappings = dict()
# Custom field_name to TS Type overrides
__mapping_overrides = dict()


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


def __get_trimmed_name(name, trim_serializer_output):
    key = "Serializer"
    return name[:-len(key)] if trim_serializer_output and name.endswith(key) else name


def __map_choices_to_union(field_type, choices):
    '''
    Generates and returns a TS union type for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Serializer Field: {field_type}')
        return 'any'

    return ' | '.join(f'"{key}"' if type(key) == str else str(key) for key in choices.keys())


def __map_choices_to_enum(enum_name, field_type, choices):
    '''
    Generates and returns a TS enum for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Serializer Field: {field_type}')
        return 'any'

    choices_enum = f"export enum {enum_name} {{\n"
    for key, value in choices.items():
        if type(key) == str:
            choices_enum = choices_enum + f"    {str(key).upper().replace(' ', '_')} = '{key}',\n"
        else:
            choices_enum = choices_enum + f"    {str(value).upper().replace(' ', '_')} = {key},\n"
    choices_enum = choices_enum + "}\n"

    return choices_enum


def __map_choices_to_enum_values(enum_name, field_type, choices):
    '''
    Generates and returns a TS enum values (display name) for all values in the provided choices OrderedDict
    '''
    if not choices:
        _LOG.warning(f'No choices specified for Serializer Field: {field_type}')
        return 'any'

    choices_enum = f"export enum {enum_name} {{\n"
    for key, value in choices.items():
        if type(key) == str:
            choices_enum = choices_enum + f"    {str(key).replace(' ', '_')} = '{value}',\n"
        else:
            "Number enums not need it"
            return None
    choices_enum = choices_enum + "}\n"

    return choices_enum


def __process_field(field_name, field, context, serializer, trim_serializer_output, camelize,
                    enum_choices, enum_values):
    '''
    Generates and returns a tuple representing the Typescript field name and Type.
    '''
    ts_enum = None
    ts_enum_value = None
    if hasattr(field, 'child'):
        is_many = True
        field_type = type(field.child)
    elif hasattr(field, 'child_relation'):
        is_many = True
        field_type = type(field.child_relation)
    else:
        is_many = False
        field_type = type(field)
    if field_type in __serializers[context]:
        ts_type = __get_trimmed_name(
            field_type.__name__, trim_serializer_output)
    elif field_type in __field_mappings[context]:
        ts_type = __field_mappings[context].get(field_type, 'any')
    elif (context in __mapping_overrides) and (serializer in __mapping_overrides[context]) \
            and field_name in __mapping_overrides[context][serializer]:
        ts_type = __mapping_overrides[context][serializer].get(
            field_name, 'any')
    elif field_type == serializers.PrimaryKeyRelatedField:
        ts_type = "number | string"
    elif (hasattr(field, 'choices') and enum_choices) or (hasattr(field, 'choices') and enum_values):
        ts_type = f"{''.join(x.title() for x in field_name.split('_'))}ChoiceEnum"
        if enum_choices:
            ts_enum = __map_choices_to_enum(ts_type, field_type, field.choices)
        if enum_values:
            ts_enum_value = __map_choices_to_enum_values(f'{ts_type}Values', field_type, field.choices)

            if not enum_choices:
                ts_type = __map_choices_to_union(field_type, field.choices)
    elif hasattr(field, 'choices'):
        ts_type = __map_choices_to_union(field_type, field.choices)
    else:
        ts_type = mappings.get(field_type, 'any')
    if is_many:
        ts_type += '[]'

    if camelize:
        field_name_components = field_name.split("_")
        field_name = field_name_components[0] + "".join(x.title() for x in field_name_components[1:])

    return field_name, ts_type, ts_enum, ts_enum_value


def __get_ts_interface_and_enums(serializer, context, trim_serializer_output, camelize, enum_choices, enum_values,
                                 annotations):
    '''
    Generates and returns a Typescript Interface by iterating
    through the serializer fields of the DRF Serializer class
    passed in as a parameter, and mapping them to the appropriate Typescript
    data type.
    '''
    name = __get_trimmed_name(serializer.__name__, trim_serializer_output)
    _LOG.debug(f"Creating interface for {name}")
    fields = []
    if hasattr(serializer, 'get_fields'):
        instance = serializer()
        fields = instance.get_fields().items()
    else:
        fields = serializer._declared_fields.items()
    ts_fields = []
    enums = []
    for key, value in fields:
        ts_property, ts_type, ts_enum, ts_enum_value = __process_field(
            key, value, context, serializer, trim_serializer_output, camelize, enum_choices, enum_values)

        if ts_enum_value is not None:
            enums.append(ts_enum_value)

        if ts_enum is not None:
            enums.append(ts_enum)

        if value.read_only or not value.required:
            ts_property = ts_property + "?"

        if value.allow_null:
            ts_type = ts_type + " | null"

        if annotations:
            annotations_list = __get_annotations(value, ts_type)
            ts_fields.append('\n'.join(annotations_list))

        ts_fields.append(f"    {ts_property}: {ts_type};")
    collapsed_fields = '\n'.join(ts_fields)
    return f'export interface {name} {{\n{collapsed_fields}\n}}\n\n', enums


def __generate_interfaces_and_enums(context, trim_serializer_output, camelize, enum_choices, enum_values, annotations):
    if context not in __serializers:
        return []
    return [__get_ts_interface_and_enums(serializer, context, trim_serializer_output, camelize,
                                         enum_choices, enum_values, annotations) for serializer in
            __serializers[context]]


def __get_enums_and_interfaces_from_generated(interfaces_enums):
    '''
    Get the interfaces and enums from the generated interfaces and enums.
    Works by splitting the tuples into two lists, one for interfaces and one for enums.
    The interfaces are not changed. The enums are compared such that there are no duplicates
    between interfaces. Then the enums are returned in string format with blank lines in between.
    '''
    interfaces, enums = [list(tup) for tup in zip(*interfaces_enums)]
    enums_string = ''
    flat_enums = [item for sublist in enums for item in sublist]
    if any(elem is not None for elem in flat_enums):
        distinct_enums = sorted(list(set(list(filter(lambda x: x is not None, flat_enums)))))
        enums_string = '\n'.join(distinct_enums) + '\n\n'
    return enums_string, interfaces


def __get_annotations(field, ts_type):
    annotations = []
    annotations.append('    /**')
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

    annotations.append('    */')

    return annotations


def generate_ts(output_path, context='default', trim_serializer_output=False, camelize=False,
                enum_choices=False, enum_values=False, annotations=False):
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
        interfaces_enums = __generate_interfaces_and_enums(context, trim_serializer_output,
                                                           camelize, enum_choices, enum_values, annotations)
        enums_string, interfaces = __get_enums_and_interfaces_from_generated(interfaces_enums)
        output_file.write(enums_string + ''.join(interfaces))


def get_ts(context='default', trim_serializer_output=False, camelize=False, enum_choices=False, enum_values=False,
           annotations=False):
    '''
    Similar to generate_ts. But rather than outputting the generated
    interfaces to the specified file, will return the generated interfaces
    as a raw string.
    '''
    interfaces_enums = __generate_interfaces_and_enums(context, trim_serializer_output, camelize,
                                                       enum_choices, enum_values, annotations)
    enums_string, interfaces = __get_enums_and_interfaces_from_generated(interfaces_enums)
    return enums_string + ''.join(interfaces)
