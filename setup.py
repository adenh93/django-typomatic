import os
import setuptools

with open('README.md') as file:
    long_description = file.read()

setuptools.setup(
    name="django-typomatic",
    version="2.1.1",
    url="https://github.com/adenh93/django-typomatic",

    author="Aden Herold",
    author_email="aden.herold1@gmail.com",

    description="A simple solution for generating Typescript interfaces from your Django Rest Framework Serializers.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=['Django', 'Django Rest Framework',
              'DRF', 'Typescript', 'Python'],

    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',

    install_requires=[
        'django',
        'djangorestframework'
    ]
)
