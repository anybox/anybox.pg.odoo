Changelog
=========

0.6 (2014-11-02)
----------------

- fixed error in Python 3
- remove tag and message of the current version after commit and revert

0.5 (2014-10-19)
----------------

- Works on Python 3.1+
- Works on Postgres 9.1 and maybe lower
- ``odb purge keeptags`` : purge all but tags
- implemented commit message
- revert now checks that the source db exists (much safer)

0.4 (2014-10-19)
----------------

- Implemented ``odb log``
- Implemented ``odb purge``
- Implemented ``odb tag`` and revert to tag
- Implemented ``odb tags``
- Renamed version to revision
- Renamed snapshot() to commit()

0.3 (2014-10-16)
----------------

- Keep the same db as the current one to work in place
- Fixed versionning and start at 1
- Also disconnect during revert operation
- Removed the unneeded tip

0.2 (2014-10-15 after sleeping)
-------------------------------

- Fixed packaging
- Fixed the ``revert`` behaviour
- Allow to revert without argument
- Improved doc

0.1 (2014-10-15)
----------------

- Initial draft
