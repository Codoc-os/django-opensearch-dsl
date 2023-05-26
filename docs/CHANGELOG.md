# Changelog

### 0.5.1 (2023-05-18)

* Change references from `opensearch-dsl-py` to `opensearch-py`.  
  This follow the deprecation notice on the
  [`opensearch-dsl-py`](https://github.com/opensearch-project/opensearch-dsl-py) project. Its features are now directly
  included in `opensearch-py`.  
  ([#33](https://github.com/Codoc-os/django-opensearch-dsl/issues/33), Contributed by [Jacob Kausler](https://github.com/jakekausler)).

## 0.5.0 (2022-11-19)

* `get_indexing_queryset()` now order unordered QuerySet by their PK.
  ([#29](https://github.com/Codoc-os/django-opensearch-dsl/issues/29), Contributed by [Cédric Raud](https://github.com/cedricraud)).
* `keep_order` argument of `django_opensearch_dsl.search.Search.to_queryset` now default to `True`
  to be in line with the documentation ([#27](https://github.com/Codoc-os/django-opensearch-dsl/issues/27)).

### 0.4.1 (2022-08-16)

* `Document.update()` method now take an optional `using` argument allowing to specify an alternate
  OpenSearch connection defined in `OPENSEARCH_DSL`.
* Fix related document automatic indexation and deletion
  (Contributed by [Colin Seifer](https://github.com/Colin-Seifer)).
* Add `pre-delete` back into `BaseSignalProcessor.handle_m2m_changed()` to  properly update the
  index on M2M interactions (Contributed by [Colin Seifer](https://github.com/Colin-Seifer)).

## 0.4.0 (2022-08-04)

* Add support for related models. See [Document Classes](document.md#django-subclass) and
  [Document Field Reference](fields.md#using-prepare_field_with_related) for more information
  (Contributed by [Colin Seifer](https://github.com/Colin-Seifer)).
* `django-opensearch-dsl` now only tests supported version of Python and Django (mainstream and LTS). 
  This choice is made to:
    * Speed up development.
    * Speed up tests.
    * Reduce actions on github.
    * Encourage people to update their stack to supported (thus safer) versions.
* Drop support for Python 3.6.
* Drop support for Django 2.1, 2.2, 3.1.
* Now supports Django 4.1.
* Now supports `opensearch-dsl>=2.0 <3.00`.

## 0.3.0 (2022-06-22)

* Fixes internal links in documentation.
* Remove the need to declare a `TESTING` boolean in `settings.py`.

## 0.2.0 (2022-01-13)

* Restore auto-sync feature (still undocumented - Contributed by [David Guillot](https://github.com/David-Guillot))
* Add support to Django 4.0 (Contributed by [David Guillot](https://github.com/David-Guillot))
* Remove some python2 leftovers (Contributed by [David Guillot](https://github.com/David-Guillot))

## 0.1.2 (2021-12-14)

* Fixed 'Search.validate()'

## 0.1.0 (2021-12-11)

* Migrated to **Opensearch**
* Drop some feature such as auto-syncing signals and related models
* Replace `search_index` management command with `opensearch`.

## 0.1.0 (2021-12-11)

* Migrated to **Opensearch**
* Drop some feature such as auto-syncing signals and related models
* Replace `search_index` management command with `opensearch`.

## Before fork from `django-elasticsearch-dsl`

### 7.1.4 (2020-07-05)

* Configure Elasticsearch _id dynamically from document (#272)
* Use chain.from_iterable in for performance improvement (#278)
* Handle case where SimpleLazyObject being treated as an Iterable (#255)
* Camelcase default value in management command (#254)
* Various updates and fixup in docs (#250, #276)
* Start testing against Python 3.8 (#266)

### 7.1.1 (2019-12-26)

* Adding detailed documentation and published to Read The Docs #222
* Resolve name resolution while delete, create index (#228)
* Added support for Django 3.0. (#230)
* Removing old Elasticsearc compatibility (#219)
* Drop StringField in favor of TextField.

### 7.1.0 (2019-10-29)

* Support for Django `DecimalField` #141
* Indexing speedup by using `parallel` indexing. #213. Now you can pass `--parallel` or set `ELASTICSEARCH_DSL_PARALLEL`
  in your settings to get indexing speed boost while indexing through management command.
* Fixing name resolution in management command #206
* Small documentation fixes. #196

### 7.0.0 (2019-08-11)

* Support Elasticsearch 7.0 (See PR #176)
* Added order by to paginate queryset properly (See PR #153)
* Remove `standard` token filter from `README.md` and test files
* Various documentation fixes

### 6.4.2 (2019-07-26)

* Fix document importing path
* Update readme

### 6.4.1 (2019-06-14)

* The `DocType` import has changed to `Document`

### 6.4.0 (2019-06-01)

* Support elasticsearch-dsl>6.3.0
* Class `Meta` has changed to class `Django` (See PR #136)
* Add `register_document` decorator to register a document (See PR #136)
* Additional Bug fixing and others

### 0.5.1 (2018-11-07)

* Limit elastsearch-dsl to supported versions

### 0.5.0 (2018-04-22)

* Add Support for Elasticsearch 6 thanks to HansAdema

### Breaking Change:

* Django string fields now point to ES text field by default.
* Nothing should change for ES 2.X but if you are using ES 5.X, you may need to rebuild and/or update some of your
  documents.

### 0.4.5 (2018-04-22)

* Fix prepare with related models when deleted (See PR #99)
* Fix unwanted calls to get_instances_from_related
* Fix for empty ArrayField (CBinyenya)
* Fix nested OneToOneField when related object doesn't exist (CBinyenya)
* Update elasticsearch-dsl minimal version

### 0.4.4 (2017-12-13)

* Fix to_queryset with es 5.0/5.1

### 0.4.3 (2017-12-12)

* Fix syncing of related objects when deleted
* Add django 2.0 support

### 0.4.2 (2017-11-27)

* Convert lazy string to string before serialization
* Readme update (arielpontes)

### 0.4.1 (2017-10-17)

* Update example app with get_instances_from_related
* Typo/grammar fixes

### 0.4.0 (2017-10-07)

* Add a method on the Search class to return a django queryset from an es result
* Add a queryset_pagination option to DocType.Meta for allow the pagination of big django querysets during the index
  populating
* Remove the call to iterator method for the django queryset
* Fix DocType inheritance. The DocType is store in the registry as a class and not anymore as an instance

### 0.3.0 (2017-10-01)

* Add support for resynching ES documents if related models are updated (HansAdema)
* Better management for django FileField and ImageField
* Fix some errors in the doc (barseghyanartur, diwu1989)

### 0.2.0 (2017-07-02)

* Replace simple model signals with easier to customise signal processors (barseghyanartur)
* Add options to disable automatic index refreshes (HansAdema)
* Support defining DocType indexes through Meta class (HansAdema)
* Add option to set default Index settings through Django config (HansAdema)

### 0.1.0 (2017-05-26)

* First release on PyPI.
