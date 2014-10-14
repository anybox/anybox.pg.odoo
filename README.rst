anybox.pg.odoo
==============

PostgreSQL database snapshotting tool for Odoo

Install
-------
::

    $ virtualenv sandbox
    $ source sandbox/bin/activate
    $ pip install anybox.pg.odoo

Usage
-----

You should first set the current database with ``odb init``::

    $ odb init demo8
    Now version 0

Then you can get the current version with ``odb info``::

    $ odb info
    database: demo8
    version : 0 (parent: 0, tip: 0)

Commit the current database to create a snapshot and a new version with ``odb commit``::

    $ odb commit
    Now version 1
    $ odb info
    database: demo8*1
    version : 1 (parent: 0, tip: 1)
    $ odb commit
    Now version 2
    $ odb commit
    Now version 3

You can revert back to a previous version of the database with ``odb revert``::

    $ odb revert 1
    Reverted to revision 1, now at revision 4
    $ odb info
    database: demo8*4
    version : 4 (parent: 1, tip: 4)



