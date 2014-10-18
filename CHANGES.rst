Changelog
=========

0.1 (2014-10-15)
----------------

- Initial draft

0.2 (2014-10-15 after sleeping)
-------------------------------

- Fixed packaging
- Fixed the ``revert`` behaviour
- Allow to revert without argument
- Improved doc

0.3 (2014-10-16)
----------------

- Keep the same db as the current one to work in place
- Fixed versionning and start at 1
- Also disconnect during revert operation
- Removed the unneeded tip

0.4 (2014-10-19)
----------------

- implemented ``odb log``
- implemented ``odb purge``
- implemented ``odb tag`` and revert to tag
- implemented ``odb tags``
- renamed version to revision
- renamed snapshot() to commit()

