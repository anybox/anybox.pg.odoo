import unittest
import time

from odb import ODB, TagExists


class TestCommit(unittest.TestCase):
    def setUp(self):
        """ create db
        """
        db = self.db = 'testodb-' + time.strftime('%Y%m%d%H%M%S')
        # create db
        ODB(db).createdb()

    def test_simple_commit(self):
        """ first simple scenario with commit and revert
        """
        odb = ODB(self.db)
        # init
        self.assertEqual(odb.init(), 1)
        self.assertEqual(odb.revision(), 1)
        self.assertEqual(odb.parent(), 0)
        # init
        self.assertEqual(odb.init(), 1)
        # commit
        odb.commit()
        self.assertEqual(odb.revision(), 2)
        self.assertEqual(odb.parent(), 1)
        # the db name remains the same
        self.assertEqual(self.db, odb.db)

        # commit
        odb.commit()
        self.assertEqual(odb.revision(), 3)
        self.assertEqual(odb.parent(), 2)

        # revert # TODO test the real revert
        odb.revert()
        self.assertEqual(odb.revision(), 3)
        self.assertEqual(odb.parent(), 2)

        # commit
        odb.commit()
        self.assertEqual(odb.revision(), 4)
        self.assertEqual(odb.parent(), 3)
        # just check that init again doesn't hurt
        self.assertEqual(odb.init(), 4)

        # revert to 2
        odb.revert(2)
        self.assertEqual(odb.revision(), 4)
        self.assertEqual(odb.parent(), 2)
        self.assertEqual(self.db, odb.db)

        # commit
        odb.commit()
        self.assertEqual(odb.revision(), 5)
        self.assertEqual(odb.parent(), 4)

        # list all revisions
        revs = odb.log()
        self.assertEqual(revs[-1]['revision'], 1)
        self.assertEqual(revs[1]['db'], self.db + '*4')
        self.assertEqual(revs[0]['revision'], 5)

        # tag revision 3 and 5
        odb.tag('v1', 3)
        odb.tag('v2')
        self.assertRaises(TagExists, odb.tag, 'v1', 4)

        # tags appear in the log
        self.assertEqual(odb.log()[2]['tag'], 'v1')
        self.assertEqual(odb.log()[0]['tag'], 'v2')

        # delete tag
        odb.tag('v2', delete=True)
        self.assertEqual(odb.log()[0].get('tag'), None)

        # we can revert to a tag
        odb.revert(tag='v1')
        revs = odb.log()
        self.assertEqual(revs[0]['revision'], 5)
        self.assertEqual(revs[0]['parent'], 3)
        # the current db has not the same tag
        self.assertEqual(odb.get('tag'), None)
        # even after commit, no tag
        odb.tag('v3')
        odb.commit()
        self.assertEqual(odb.get('tag'), None)

        # purge without confirmation does nothing
        odb.purge('all')
        self.assertEqual(len(odb.log()), 6)

        # check for real
        odb.purge('all', confirm=True)
        self.assertEqual(len(odb.log()), 1)

    def tearDown(self):
        """ cleanup
        """
        # drop everything (even if tests failed)
        odb = ODB(self.db)
        odb.purge('all', confirm=True)
        odb.dropdb()
