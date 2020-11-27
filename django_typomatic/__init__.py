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


def __process_field(field_name, field, context, serializer):
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
        ts_type = field_type.__name__
    elif field_type in __field_mappings[context]:
        ts_type = __field_mappings[context].get(field_type, 'any')
    elif (context in __mapping_overrides) and (serializer in __mapping_overrides[context]) and field_name in __mapping_overrides[context][serializer]:
        ts_type = __mapping_overrides[context][serializer].get(
            field_name, 'any')
    else:
        ts_type = mappings.get(field_type, 'any')
    if is_many:
        ts_type += '[]'
    return (field_name, ts_type)


def __get_ts_interface(serializer, context):
    '''
    Generates and returns a Typescript Interface by iterating
    through the serializer fields of the DRF Serializer class
    passed in as a parameter, and mapping them to the appropriate Typescript
    data type.
    '''
    name = serializer.__name__
    _LOG.debug(f"Creating interface for {name}")
    fields = []
    if hasattr(serializer, 'get_fields'):
        instance = serializer()
        fields = instance.get_fields().items()
    else:
        fields = serializer._declared_fields.items()
    ts_fields = []
    for key, value in fields:
        ts_field = __process_field(key, value, context, serializer)
        if value.read_only or not value.required:
            op = '?:'
        else:
            op = ':'
        ts_fields.append(f"    {ts_field[0]}{op} {ts_field[1]};")
    collapsed_fields = '\n'.join(ts_fields)
    return f'export interface {name} {{\n{collapsed_fields}\n}}\n\n'


def __generate_interfaces(context):
    if context not in __serializers:
        return []
    return [__get_ts_interface(serializer, context)
            for serializer in __serializers[context]]


def generate_ts(output_path, context='default'):
    '''
    When this function is called, a Typescript interface will be generated
    for each DRF Serializer in the serializers dictionary, depending on the
    optional context parameter provided. If the parameter is ignored, all
    serializers in the default value, 'default' will be iterated over and a
    list of Typescript interfaces will be returned via a list comprehension.

    The Typescript interfaces will then be outputted to the file provided.
    '''
    with open(output_path, 'w') as output_file:
        interfaces = __generate_interfaces(context)
        print(interfaces)
        output_file.write(''.join(interfaces))


def get_ts(context='default'):
    '''
    Similar to generate_ts. But rather than outputting the generated 
    interfaces to the specified file, will return the generated interfaces 
    as a raw string.
    '''
    interfaces = __generate_interfaces(context)
    return ''.join(interfaces)
