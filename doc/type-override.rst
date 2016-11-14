Type Overrides
==============

If the type detector does not correctly identify the types of your spreadsheet columns,
you can override them in the config file based on the dataset name::

    import messytables
    TYPE_OVERRIDES = [{
        'dataset': 'my_dataset',
        'fields': {
            'My Column': messytables.StringType,
        }
    }]
