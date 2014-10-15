anybox.pg.odoo
==============

This tool basically manages versionned snapshots of the current database,
mimicking the common workflow of VCS tools such as init, commit, revert.  It
was first created to snapshot Odoo databases but may be easily modified to be
agnostic.

Install
-------

Install as any normal Python distribution, in a virtualenv, buildout or
system-wide. The only current dependency is `psycopg2
<https://pypi.python.org/pypi/psycopg2/>`_ >= 2.5.

Example with a virtualenv::

    $ virtualenv sandbox
    $ source sandbox/bin/activate
    $ pip install anybox.pg.odoo

Example in a dedicated part of a buildout::

    [odb]
    recipe = zc.recipe.egg
    eggs = anybox.pg.odoo

Usage
-----

First read the available commands with ``odb -h``::

    $ odb -h
    usage: odb [-h] {init,commit,info,revert} ...
    
    PostgreSQL snapshot versionning tool for Odoo
    
    positional arguments:
      {init,commit,info,revert}
                            sub-commands
        init                Set the current db
        commit              Save the current db in a new revision
        info                Display the revision of the current db
        revert              Drop the current db and clone from a previous revision
    
    optional arguments:
      -h, --help            show this help message and exit
 

You should first set the current database with ``odb init``::

    $ odb init demo8
    Now version 1

Then you can get the current version with ``odb info``::

    $ odb info
    database: demo8
    version : 1 (parent: 0)

Commit the current database to create a snapshot and a new version with ``odb commit``::

    $ odb commit
    Now version 2
    $ odb info
    database: demo8
    version : 2 (parent: 1)
    $ odb commit
    Now version 3
    $ odb commit
    Now version 4

You can revert back to the last version of the database (the parent) with ``odb revert``::

    $ odb revert
    Reverted to parent 3, now at revision 4

You can also revert back to any previous version::

    $ odb revert 2
    Reverted to parent 2, now at revision 5
    $ odb info
    database: demo8
    version : 5 (parent: 2)

How it works and pollutes
-------------------------

- It uses the ``CREATE DATABASE FROM TEMPLATE`` feature of PostgreSQL
- It currently stores version information in the ``ir_config_parameter`` table
  of Odoo (though this will change in the future).
- It expects that the connection to PostgreSQL is done through Unix Domain
  Socket with the current user being allowed to create and drop databases.
- It stores the current database in ``~/.anybox.pg.odoo``

what's next? (todo list)
------------------------

- Use a dedicated database to store version information instead of the ``ir_config_parameter`` table
- Fix obvious bugs
- Python 3 compatibility
- Implement tagging
- Allow to drop all untagged databases
- Improve the database naming scheme
- Try to make the system transactional

Contribute
----------

Mercurial repository and bug tracker: https://bitbucket.org/anybox/anybox.pg.odoo

