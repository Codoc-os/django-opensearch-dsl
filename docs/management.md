# Management Command

## Summary

```text
usage: manage.py opensearch [-h] [--version] [-v {0,1,2,3}] [--settings SETTINGS]
                            [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                            [--force-color] {list,index,document} ...

Allow to create and delete indices, as well as indexing, updating, or deleting specific
documents from specific indices.

positional arguments:
  {list,index,document}
    list                Show all available indices (and their state) for the current project.
    index               Manage the creation and deletion of indices.
    document            Manage the indexation and creation of documents.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v {0,1,2,3}, --verbosity {0,1,2,3}
                        Verbosity level; 0=minimal output, 1=normal output, 2=verbose output,
                        3=very verbose output
  --settings SETTINGS   The Python path to a settings module, e.g. "myproject.settings.main".
                        If this isn't provided, the DJANGO_SETTINGS_MODULE environment variable
                        will be used.
  --pythonpath PYTHONPATH
                        A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".
  --traceback           Raise on CommandError exceptions
  --no-color            Don't colorize the command output.
  --force-color         Force colorization of the command output
```

Indices and documents can be managed through the `opensearch` management command. This command contains 3 subcommands :

* `index` - Manage indices creation / deletion.
* `list` - List for each application which indices are created or not, as well as the number of documents indexed for
  created indices.
* `document` - Manage documents creation / deletion / update.

## `index` Subcommand

### Summary

```text
usage: manage.py opensearch index [-h] [--suffix SUFFIX] [--force]
                                  [--ignore-error]
                                  {create,delete} [INDEX [INDEX ...]]

Manage the deletion of indices.

positional arguments:
  {create,delete}  Whether you want to create or delete the indices.
  INDEX            Only manage the given indices.

optional arguments:
  -h, --help       show this help message and exit
  --suffix SUFFIX  A suffix for the index name to create/delete (if you don't
                   provide one, a timestamp will be used for creation).
  --force          Do not ask for confirmation.
  --ignore-error   Do not stop on error.
```

### Description

This command takes a mandatory positional argument:

* `create` - Create the indices.
* `delete` - Delete the indices.

The command can also take any number of optional positional arguments which are the names of the indices that should be
created/deleted. If no index is provided, the action is applied to all indices.

Use the `--force` options to bypass the confirmation step, and use the `--ignore-error` option to not stop on error (such as
trying to create an already created index).

## `list` Subcommand

The `list` subcommand displays a summary of each index, indicated whether they are created or not, and the number of
document indexed.

Sample output :

```text
django_dummy_app
[X] country. Following indices exist:
    - country--20220813172923248055 Active (0 documents)
    - country--20220813172923212345 (0 documents)
[ ] continent. Following indices exist:
    - continent--20220813172923248055 (0 documents)
[X] event (2361 documents)
```

## `document` Subcommand

### Summary

```text
usage: manage.py opensearch document [-h] [-f [FILTERS [FILTERS ...]]]
                                     [-e [EXCLUDES [EXCLUDES ...]]] [--force]
                                     [--index-suffix INDEX_SUFFIX]
                                     [-i [INDICES [INDICES ...]]] [-c COUNT]
                                     [-p] [-r] [-m]
                                     {index,delete,update,migrate}

Manage the indexation and creation of documents.

positional arguments:
  {index,delete,update,migrate}
                        Whether you want to index, delete or update documents in indices. Or migrate from an index to another.

optional arguments:
  -h, --help            show this help message and exit
  -f [FILTERS [FILTERS ...]], --filters [FILTERS [FILTERS ...]]
                        Filter object in the queryset. Argument must be formatted as '[lookup]=[value]', e.g. 'document_date__gte=2020-05-21.
                        The accepted value type are:
                          - 'None' ('[lookup]=')
                          - 'float' ('[lookup]=1.12')
                          - 'int' ('[lookup]=23')
                          - 'datetime.date' ('[lookup]=2020-10-08')
                          - 'list' ('[lookup]=1,2,3,4') Value between comma ',' can be of any other accepted value type
                          - 'str' ('[lookup]=week') Value that didn't match any type above will be interpreted as a str
                        The list of lookup function can be found here: https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups
  -e [EXCLUDES [EXCLUDES ...]], --excludes [EXCLUDES [EXCLUDES ...]]
                        Exclude objects from the queryset. Argument must be formatted as '[lookup]=[value]', see '--filters' for more information
  --force               Do not ask for confirmation.
  --index-suffix INDEX_SUFFIX
                        The suffix for the index name (if you don't provide one, the current index will be used). Required for `migrate` subcommand.
  -i [INDICES [INDICES ...]], --indices [INDICES [INDICES ...]]
                        Only update documents on the given indices.
  -c COUNT, --count COUNT
                        Update at most COUNT objects (0 to index everything).
  -p, --parallel        Parallelize the communication with Opensearch.
  -r, --refresh         Make operations performed on the indices immediatly available for search.
  -m, --missing         When used with 'index' action, only index documents not indexed yet.
```

### Description

This command allows you to index your model into Opensearch. It takes a required positional argument :

* `index` Index the documents, already indexed documents will be reindexed if you do not use the `--missing` option.
* `delete` Documents will be deleted from the index.
* `update` Update already indexed documents.
* `migrate` Migrate from an index to another (by switching index alias)

***Choosing indices***

The default behavior is to apply the action to every registered index. You can choose which indices you want to apply the
action on using the `--indices` option.

***Choosing data***

The data used for the action will retrieve using the `get_indexing_queryset()` and `get_queryset()` method of your
`Document` subclass (see [Indexing data](document.md#indexing-data)). You can use the `--filters` and `--excludes`
options to filter down the queryset. These options take argument formatted like *kwargs* given to the `filter()`
and `exclude()` `QuerySet`'s method (`[lookup]=[value]`).

For instance, if you want to index only the models created in 2020, you can
do `-f creation_date__gte=2020-01-01 creation_date__lte=2020-12-31`. If you want to delete all text not containing the
word "fruit", you can do `-e content__icontains=fruit`.

For the list of lookup functions,
see [QuerySet's fields lookup](https://docs.djangoproject.com/en/dev/ref/models/querysets/#field-lookups).

Values are parsed in different types according to how they are formatted. Accepted types are:

* `None` (`[lookup]=`)
* `float` (`[lookup]=1.12`)
* `int` (`[lookup]=23`)
* `datetime.datetime` (`[lookup]=2020-10-08`) - Must be a valid [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) date.
* `list` (`[lookup]=1,2,3,4`) - Value between comma `,` can be of any other accepted value type.

Values that didn't match any type above will be interpreted as an `str`.

***Caution:*** *The given lookup must be valid for all indices, i.e. for every index, given `filters`/`excludes` must
be valid for the attached `Model`. Use the `--indices` option to choose which indices you want to apply the action on.*

Finally, you can use the `--count [COUNT]` option to index/delete/update only up to `COUNT` document per index.

***Other Options***

* `--refresh` - Make operations performed on the indices immediately available for search.
  See [Refresh API](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-refresh.html) for more
  information.
* `--force` - Bypass confirmation step.
* `--parallel` - Parallelize the communication with Opensearch.
