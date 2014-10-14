import unittest
import time
import psycopg2

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
        self.assertEqual(odb.init(), 0)
        self.assertEqual(odb.version(), 0)
        self.assertEqual(odb.parent(), 0)
        # init
        self.assertEqual(odb.init(), 0)
        # snapshot
        odb.snapshot()
        self.assertEqual(odb.version(), 1)
        self.assertEqual(odb.parent(), 0)

        # snapshot
        odb.snapshot()
        self.assertEqual(odb.version(), 2)
        self.assertEqual(odb.parent(), 1)
        self.assertEqual(odb.db, self.db + '_2')

        # revert
        odb.revert(1)
        self.assertEqual(odb.version(), 3)
        self.assertEqual(odb.parent(), 1)

        # snapshot (new branch)
        odb.snapshot()
        self.assertEqual(odb.version(), 4)
        self.assertEqual(odb.parent(), 3)
        self.assertEqual(odb.init(), 4)

    def tearDown(self):
        """ cleanup test databases
        """
        odb = ODB(self.db)
        odb.dropdb()
