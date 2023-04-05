# django-typomatic ![pypi badge](https://img.shields.io/pypi/v/django-typomatic)

_A simple solution for generating Typescript interfaces from your [Django Rest Framework Serializers](https://www.django-rest-framework.org/api-guide/serializers/)._

Since I now require a simple package to generate Typescript interfaces for Django Rest Framework serializers, I've decided to port over my [Typemallow](https://github.com/adenh93/typemallow/) package for use with DRF serializers!

## Usage:

_Using django-typomatic is just as simple!_

First, install the package
`pip install django-typomatic`

### Option 1: Decorators

For your Django Rest Framework serializers that you wish to generate Typescript interfaces for, simply import `ts_interface` and `generate_ts` from the `django_typomatic` module, and add the `@ts_interface()` class decorator to your Django Rest Framework serializer class.

All that is required to generate your Typescript interfaces is to call the `generate_ts()` function, and provide a filepath as a parameter to output the result.

_main.py_

```python
from django_typomatic import ts_interface, generate_ts
from rest_framework import serializers


@ts_interface()
class Foo(serializers.Serializer):
    some_field = serializers.CharField()
    another_field = serializers.DateTimeField()


generate_ts('./output.ts')
```

_output.ts_

```typescript
export interface Foo {
  some_field: string;
  another_field: date;
}
```

Alternatively, you can call `get_ts()`, which will return the generated interfaces as a raw string, rather than writing the results to a file:

_main.py_

```python
from django_typomatic import ts_interface, get_ts
from rest_framework import serializers


@ts_interface()
class Foo(serializers.Serializer):
    some_field = serializers.ListField(child=serializers.IntegerField())
    another_field = serializers.CharField()

print(get_ts())
```

which outputs the following string:

`export interface Foo {\n some_field: number[];\n another_field: string;\n}\n\n`

_django-typomatic_ supports nested serializers, as well as list fields and other fields that act as lists (any field with many=True)

_main.py_

```python
from django_typomatic import ts_interface, generate_ts
from rest_framework import serializers


@ts_interface()
class Foo(serializers.Serializer):
    some_field = serializers.ListField(child=serializers.IntegerField())
    another_field = serializers.CharField()


@ts_interface()
class Bar(serializers.Serializer):
    foo = Foo()
    foos = Foo(many=True)
    bar_field = serializers.CharField()
```

_output.ts_

```typescript
export interface Foo {
  some_field: number[];
  another_field: string;
}

export interface Bar {
  foo: Foo;
  foos: Foo[];
  bar_field: string;
}
```

_django-typomatic_ also supports ChoiceField serializers, as well as any other serializer fields that makes use of choices.

_main.py_

```python
from django_typomatic import ts_interface
from rest_framework import serializers
from django.db import models


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

```

_output.ts_

```typescript
export interface ActionSerializer {
  action: "Action1" | "Action2" | "Action3";
  num: 1 | 2 | 3;
}
```

#### Extended Usage:

The `@ts_interface()` decorator function accepts an optional parameter, _context_, which defaults to... well... 'default'.

"_Why is this the case?_"

When a Serializer is identified with with `@ts_interface` decorator, it is added to a list in a dictionary of serializers, with the dictionary key being the value provided to the _context_ parameter. If you were to provide different contexts for each serializer, additional keys will be created if they do not exist, or the serializer will simply be appended to the list at the existing key.

This comes in handy, as the `generate_ts()` function _also_ accepts an optional _context_ parameter, which will filter only serializers in the dictionary at the specific key.

This is useful if you wish to output different contexts to different files, e.g.

_main.py_

```python
...
from django_typomatic import ts_interface, generate_ts
from rest_framework import serializers


@ts_interface(context='internal')
class Foo(serializers.Serializer):
    foo = serializers.CharField()


@ts_interface(context='internal')
class Bar(serializers.Serializer):
    bar = serializers.CharField()


@ts_interface(context='external')
class FooBar(serializers.Serializer):
    foo_bar = serializers.CharField()


'''
we're telling django-typomatic that we only want to generate interfaces from serializers with
an 'internal' context to './internal.ts'
'''
generate_ts('./internal.ts', context='internal')

'''
only generate interfaces from serializers with an 'external' context to './external.ts'
'''
generate_ts('./external.ts', context='external')
```

_internal.ts_

```typescript
export interface Foo {
  foo: string;
}

export interface Bar {
  bar: string;
}
```

_external.ts_

```typescript
export interface FooBar {
  foo_bar: string;
}
```

#### Camelize

You can use django dependencies that converts the response from `snake_casing` to `camelCasing`. The solution offered for this is camelize:

```python
from django_typomatic import ts_interface, generate_ts
from rest_framework import serializers


@ts_interface()
class Foo(serializers.Serializer):
    some_field = serializers.CharField()


generate_ts('./output.ts', camelize=True)
```

Different from the main example. The interface attributes are now camel casing.

_output.ts_

```typescript
export interface Foo {
  someField: string;
}
```

#### TypeScript enums from ChoiceFields
_django-typomatic_ also allows for generating an `enum` for a ChoiceField. The `enum` will follow the naming of `ModelFieldNameChoiceEnum` for a model field with the name `model_field_name`, note that the interface field still remains `model_field_name`.

_main.py_

```python
from django_typomatic import ts_interface
from rest_framework import serializers
from django.db import models


class ActionType(models.TextChoices):
    ACTION1 = "Action1", ("Action1")
    ACTION2 = "Action2", ("Action2")
    ACTION3 = "Action3", ("Action3")


class NumberType(models.IntegerChoices):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@ts_interface('enumChoices')
class ChoiceSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ActionType.choices)
    num = serializers.ChoiceField(choices=NumberType.choices)

```

_output.ts_

```typescript
export enum ActionChoiceEnum {
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
```

## Option 2: CLI (Preferred)

Since version 2.1, you can now generate all interfaces via a CLI. This will be the preferred method going forward, as you will no longer need to decorate your serializers, or manually call the `generate_ts` function, resulting in less complexity overall.

**NOTE:** In order to use the CLI, you will need to add `django-typomatic` to `INSTALLED_APPS`.

Special thanks to @bigpe for brewing up the first version of this CLI!

### Usage

```
--serializers [SERIALIZERS ...], -s [SERIALIZERS ...]
                         Serializers enumeration formats: module_name.SerializerName | module_name
   --all Generate TS types for all project serializers
   --trim, -t Trim "serializer" from type name
   --camelize, -c Camelize field names
   --annotations, -a Add js doc annotations for validations (eg. for Zod)
   --enum_choices, -ec Add choices to external enum type instead union
   --enum_values, -ev Add enum to obtain display name for choices field
```

Using the new `generate_ts` management command, you can fine tune the generation of your interfaces similarly to how you would via the decorator method, with some additional functionality. For example, you can call the command with the `--all` flag and get all the generated types to the folder specified (they will be grouped by the application name, all external applications will be excluded, only the project applications).

You can also generate modules separately, as an example, `-s user` will restrict generation to all serializers in the `user` application, and `-s user.UserSerializer` will restrict generation to just the `UserSerializer` serializer belonging to the `user` application.

### Examples

_Generate TS for `user` app_

`./manage.py generate_ts -s user`

_Generate TS for specific serializer from user app_

`./manage.py generate_ts -s user.UserSerializer`

_Generate TS for many apps or serializers_

`./manage.py generate_ts -s user.UserSerializer group role.RoleSerializer role.RoleListSerializer`

_Generate TS for user app with annotations, choices enums, trim serializer, camelize, enum values and custom output path_

`./manage.py generate_ts -s user -a -ec -t -c -ev -o "./custom_folder/"`


