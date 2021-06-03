import logging
from rest_framework import serializers
from .mappings import mappings

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


def __process_field(field_name, field, context, serializer, trim_serializer_output, camelize):
    '''
    Generates and returns a tuple representing the Typescript field name and Type.
    '''
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
    elif (context in __mapping_overrides) and (serializer in __mapping_overrides[context]) and field_name in __mapping_overrides[context][serializer]:
        ts_type = __mapping_overrides[context][serializer].get(
            field_name, 'any')
    else:
        ts_type = mappings.get(field_type, 'any')
    if is_many:
        ts_type += '[]'

    if camelize:
        field_name_components = field_name.split("_")
        field_name = field_name_components[0] + "".join(x.title() for x in field_name_components[1:])

    return (field_name, ts_type)


def __get_ts_interface(serializer, context, trim_serializer_output, camelize):
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
    for key, value in fields:
        property, type = __process_field(
            key, value, context, serializer, trim_serializer_output, camelize)

        if value.read_only or not value.required:
            property = property + "?"

        if value.allow_null:
            type = type + " | null"

        ts_fields.append(f"    {property}: {type};")
    collapsed_fields = '\n'.join(ts_fields)
    return f'export interface {name} {{\n{collapsed_fields}\n}}\n\n'


def __generate_interfaces(context, trim_serializer_output, camelize):
    if context not in __serializers:
        return []
    return [__get_ts_interface(serializer, context, trim_serializer_output, camelize)
            for serializer in __serializers[context]]


def generate_ts(output_path, context='default', trim_serializer_output=False, camelize=False):
    '''
    When this function is called, a Typescript interface will be generated
    for each DRF Serializer in the serializers dictionary, depending on the
    optional context parameter provided. If the parameter is ignored, all
    serializers in the default value, 'default' will be iterated over and a
    list of Typescript interfaces will be returned via a list comprehension.

    The Typescript interfaces will then be outputted to the file provided.
    '''
    with open(output_path, 'w') as output_file:
        interfaces = __generate_interfaces(context, trim_serializer_output, camelize)
        output_file.write(''.join(interfaces))


def get_ts(context='default', trim_serializer_output=False, camelize=False):
    '''
    Similar to generate_ts. But rather than outputting the generated 
    interfaces to the specified file, will return the generated interfaces 
    as a raw string.
    '''
    interfaces = __generate_interfaces(context, trim_serializer_output, camelize)
    return ''.join(interfaces)
