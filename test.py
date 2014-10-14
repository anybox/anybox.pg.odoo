import unittest
import time
import psycopg2

from odb import ODB, AlreadyInitialized


class TestCommit(unittest.TestCase):
    def setUp(self):
        """ create db
        """
        db = self.db = 'testodb' + time.strftime('%Y%m%d%H%M%S')
        # create db
        ODB(db).createdb()

    def test_simple_commit(self):
        """ first simple scenario with commit and revert
        """
        odb = ODB(self.db)
        # init version
        self.assertEqual(odb.init(), 0)
        self.assertEqual(odb.version(), 0)
        self.assertEqual(odb.parent(), 0)
        # retry the same
        with self.assertRaises(AlreadyInitialized):
            odb.init()
        # commit version 1
        odb.commit()
        self.assertEqual(odb.version(), 1)
        self.assertEqual(odb.parent(), 0)

        # commit version 2
        odb.commit()
        self.assertEqual(odb.version(), 2)
        self.assertEqual(odb.parent(), 1)
        self.assertEqual(odb.db, self.db + '_2')

        # revert to version 1
        odb.revert(1)
        self.assertEqual(odb.version(), 3)
        self.assertEqual(odb.parent(), 1)

        # commit version 4 (new branch)
        odb.commit()
        self.assertEqual(odb.version(), 4)
        self.assertEqual(odb.parent(), 3)

    def tearDown(self):
        """ cleanup test databases
        """
        odb = ODB(self.db)
        odb.dropdb()
