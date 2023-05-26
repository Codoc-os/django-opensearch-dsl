"""Setuptools entry point."""
import codecs
import os

from setuptools import setup

DIRNAME = os.path.dirname(__file__)
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Framework :: Django',
    'Framework :: Django :: 3.2',
    'Framework :: Django :: 4.0',
    'Framework :: Django :: 4.1',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
]
LONG_DESCRIPTION = (
    codecs.open(os.path.join(DIRNAME, 'README.md'), encoding='utf-8').read()
    + '\n'
    + codecs.open(os.path.join(DIRNAME, 'docs/CHANGELOG.md'), encoding='utf-8').read()
)
REQUIREMENTS = [
    'opensearch-py>=2.2.0',
    'dateutils'
]

setup(
    name='django-opensearch-dsl',
    version='0.5.1',
    description="""Wrapper around opensearch-py for django models""",
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Quentin Coumes (Codoc)',
    author_email='coumes.quentin@gmail.com',
    url='https://github.com/qcoumes/django-opensearch-dsl',
    packages=['django_opensearch_dsl'],
    include_package_data=True,
    install_requires=REQUIREMENTS,
    license="Apache Software License 2.0",
    keywords='django elasticsearch elasticsearch-dsl opensearch opensearch-dsl opensearch-py',
    classifiers=CLASSIFIERS,
)
