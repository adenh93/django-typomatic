from rest_framework import serializers
from .mappings import mappings

__serializers = dict()


def ts_interface(context='default'):
    '''
    Any valid Django Rest Framework Serializers with this class decorator will
    be added to a list in a dictionary. An optional parameter: 'context'
    may be provided, which will create separate dictionary keys per context.
    Otherwise, all values will be inserted into a list with a key of 'default'.
    e.g.
    @ts_interface(context='internal')
    class Foo(serializers.Serializer):
        bar = serializer.IntegerField()
    '''
    def decorator(cls):
        if issubclass(cls, serializers.Serializer):
            if context not in __serializers:
                __serializers[context] = []
            __serializers[context].append(cls)
        return cls
    return decorator


def __get_ts_interface(serializer, context):
    '''
    Generates and returns a Typescript Interface by iterating
    through the serializer fields of the DRF Serializer class
    passed in as a parameter, and mapping them to the appropriate Typescript
    data type.
    '''
    name = serializer.__name__
    ts_fields = []
    for key, value in serializer._declared_fields.items():
        is_many = hasattr(value, 'child')
        value_type = is_many and type(value.child) or type(value)
        if value_type in __serializers[context]:
            ts_type = value_type.__name__
        else:
            ts_type = mappings.get(value_type, 'any')

        if is_many:
            ts_type += '[]'

        ts_fields.append(
            f'\t{key}: {ts_type};'
        )
    ts_fields = '\n'.join(ts_fields)
    return f'export interface {name} {{\n{ts_fields}\n}}\n\n'


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
        interfaces = [__get_ts_interface(serializer, context)
                      for serializer in __serializers[context]]
        output_file.write(''.join(interfaces))
