from typing import Literal

FORMATS = Literal[
    'email',
    'url',
    'uuid',
    'date-time',
    'date',
    'time',
    'double',
]

def ts_format(format: FORMATS): ...
def ts_field(ts_type: str, context='default'): ...
def ts_interface(context='default', mapping_overrides=None): ...
def generate_ts(output_path, context='default', trim_serializer_output=False, camelize=False,
                enum_choices=False, enum_values=False, enum_keys=False, annotations=False): ...
def get_ts(context='default', trim_serializer_output=False, camelize=False, enum_choices=False,
           enum_values=False, enum_keys=False, annotations=False): ...

