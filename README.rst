anybox.pg.odoo
==============

This tool basically manages versionned snapshots of the current database,
mimicking the common workflow of VCS tools such as init, commit, revert, log, etc.
It was first created to snapshot Odoo databases but may be easily modified to be
agnostic.

.. contents::

Install
-------

This tool works on Python 2.7 and Python 3.x.
Install as any normal Python distribution, in a virtualenv, buildout or
system-wide. The only current dependency is `psycopg2
<https://pypi.python.org/pypi/psycopg2/>`_ >= 2.5.

Example with a virtualenv::

    $ virtualenv sandbox && source sandbox/bin/activate
    $ pip install anybox.pg.odoo

Usage
-----

First read the available commands with ``odb -h``.
You get the available commands::

        init                Set the current db
        commit              Save the current db in a new revision
        info                Display the revision of the current db
        revert              Drop the current db and clone from a previous revision
        log                 List all available revisions
        purge               Destroy revisions
        tags                List all tags
        tag                 Tag a specific revision


You should first set the current database with ``odb init``::

    $ odb init demo8
    Now revision 1

Then you can get the current revision with ``odb info``::

    $ odb info
    database: demo8
    revision : 1 (parent: 0)

Commit the current database to create a snapshot and a new revision with ``odb commit``::

    $ odb commit
    Now revision 2
    $ odb info
    database: demo8
    revision : 2 (parent: 1)
    $ odb commit
    Now revision 3
    $ odb commit
    Now revision 4

You can revert back to the last revision of the database (the parent) with ``odb revert``::

    $ odb revert
    Reverted to parent 3, now at revision 4

You can also revert back to any previous revision::

    $ odb revert 2
    Reverted to parent 2, now at revision 4
    $ odb info
    database: demo8
    revision : 4 (parent: 2)

You can put tags on a revision, revert to a tag and delete a tag with ``odb tag`` and ``odb tags``::

    $ odb tag v1 2
    $ odb tag v2 3
    $ odb tags
    v2 (demo8*3)
    v1 (demo8*2)
    $ odb revert v1
    Reverted to parent 2, now at revision 4
    $ odb tag -d v1

The you can display all the revisions with ``odb log``::

    $ odb log
    demo8:
        revision: 4
        parent: 2
    demo8*3:
        revision: 3
        parent: 2
        tag: v2
    demo8*2:
        revision: 2
        parent: 1
    demo8*1:
        revision: 1
        parent: 0

Then you can purge all the revisions except the tags::

    $ odb purge keeptags

or all the revisions::

    $ odb purge all




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
- Implement diff (#fear)
- Improve the database naming scheme

Contribute
----------

Mercurial repository and bug tracker: https://bitbucket.org/anybox/anybox.pg.odoo

Run tests with::

    $ python setup.py test
