import unittest
import time

from odb import ODB


class TestCommit(unittest.TestCase):
    def setUp(self):
        """ create db
        """
        db = self.db = 'testodb-' + time.strftime('%Y%m%d%H%M%S')
        # create db
        ODB(db).createdb()

    def test_simple_commit(self):
        """ first simple scenario with snapshot and revert
        """
        odb = ODB(self.db)
        # init
        self.assertEqual(odb.init(), 1)
        self.assertEqual(odb.revision(), 1)
        self.assertEqual(odb.parent(), 0)
        # init
        self.assertEqual(odb.init(), 1)
        # snapshot
        odb.snapshot()
        self.assertEqual(odb.revision(), 2)
        self.assertEqual(odb.parent(), 1)
        # the db name remains the same
        self.assertEqual(self.db, odb.db)

        # snapshot
        odb.snapshot()
        self.assertEqual(odb.revision(), 3)
        self.assertEqual(odb.parent(), 2)

        # revert # TODO test the real revert
        odb.revert()
        self.assertEqual(odb.revision(), 3)
        self.assertEqual(odb.parent(), 2)

        # snapshot
        odb.snapshot()
        self.assertEqual(odb.revision(), 4)
        self.assertEqual(odb.parent(), 3)
        # just check that init again doesn't hurt
        self.assertEqual(odb.init(), 4)

        # revert to 2
        odb.revert(2)
        self.assertEqual(odb.revision(), 4)
        self.assertEqual(odb.parent(), 2)
        self.assertEqual(self.db, odb.db)

        # snapshot
        odb.snapshot()
        self.assertEqual(odb.revision(), 5)
        self.assertEqual(odb.parent(), 4)

        # list all revisions
        revs = odb.log()
        self.assertEqual(revs[-1]['revision'], '1')
        self.assertEqual(revs[1]['db'], self.db + '*4')
        self.assertEqual(revs[0]['revision'], '5')

        # purge all revisions
        odb.purge('all')

        # for teardown
        self.last = odb.revision()

    def tearDown(self):
        """ cleanup
        """
        # clean the current db
        odb = ODB(self.db)
        odb.purge('all')
        odb.dropdb()
