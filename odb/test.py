import unittest
import time

from .odb import ODB, TagExists, NoTemplate


class TestCommit(unittest.TestCase):
    def setUp(self):
        """ create db
        """
        db = self.db = 'testodb-' + time.strftime('%Y%m%d%H%M%S')
        # create db
        ODB(db)._createdb()

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

        # commit with a message
        odb.commit(msg='commit message')
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
        # just check that init again doesn't hurt even when passing another revision
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
        self.assertEqual(revs[-2]['message'], 'commit message')

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

        # test odb log limit 2
        revs = odb.log(limit=1)
        self.assertEqual(len(revs), 1)
        revs = odb.log(limit=2)
        self.assertEqual(len(revs), 2)
        revs = odb.log(limit=3)
        self.assertEqual(len(revs), 3)
        revs = odb.log(limit=3, reversed=False)
        self.assertEqual(len(revs), 3)
        revs = odb.log(limit=2, reversed=False)
        self.assertEqual(len(revs), 2)
        revs = odb.log(limit=1, reversed=False)
        self.assertEqual(len(revs), 1)
        # test odb log limit greater than number of commit
        revs = odb.log(limit=150)
        self.assertEqual(len(revs), len(odb.log()))
        revs = odb.log(limit=150, reversed=False)
        self.assertEqual(len(revs), len(odb.log()))

        # delete the tag
        odb.tag('v3', delete=True)

        # revert to a non existant revision
        self.assertRaises(NoTemplate, odb.revert, 99)

        # purge without confirmation does nothing
        odb.purge('keeptags')
        self.assertEqual(len(odb.log()), 6)

        # purge all except tags
        purged = odb.purge('keeptags', confirm=True)
        self.assertEqual(len(purged), 4)
        self.assertEqual(len(odb.log()), 2)

        # check for real
        odb.purge('all', confirm=True)
        self.assertEqual(len(odb.log()), 1)

    def test_connection_string(self):
        odb = ODB(self.db)
        self.assertEqual(
            'dbname=%s' % self.db,
            odb._get_connection_string()
        )
        self.assertEqual(
            'dbname=%s host=hostname' % self.db,
            odb._get_connection_string(host="hostname")
        )
        self.assertEqual(
            'dbname=%s user=ccomb host=hostname' % self.db,
            odb._get_connection_string(host='hostname', user='ccomb')
        )
        self.assertEqual(
            'dbname=%s user=ccomb host=hostname port=5433' % self.db,
            odb._get_connection_string(host='hostname', user='ccomb', port="5433")
        )
        self.assertEqual(
            'dbname=%s user=ccomb password=**** host=hostname port=5433' % self.db,
            odb._get_connection_string(user='ccomb', password='****',
                                       host='hostname', port="5433")
        )
        # this is need to avoid to crash on tearDown
        odb.init()

    def test_glog(self):
        odb = ODB(self.db)
        # this is need to avoid to crash on tearDown
        odb.init()
        self.assertEqual(2, odb._nb_interval(0))
        self.assertEqual(2, odb._nb_interval(1))
        self.assertEqual(2, odb._nb_interval(2))
        self.assertEqual(4, odb._nb_interval(3))
        self.assertEqual(6, odb._nb_interval(4))
        self.assertEqual(8, odb._nb_interval(5))
        revs = [{'db': 'test*1',
                 'message': 'commit 1',
                 'parent': 0,
                 'revision': 1,
                 'tag': 'tag1'},
                {'db': 'test*2',
                 'message': 'commit 2',
                 'parent': 1,
                 'revision': 2,
                 'tag': 'tag2'},
                ]
        output = odb._glog_output(revs)
        expected = ['o\t2: commit 2', '|', '|', 'o\t1: commit 1']
        self.assertEqual(expected, output)
        revs = [{'db': 'test*1',
                 'message': 'commit 1',
                 'parent': 0,
                 'revision': 1,
                 'tag': 'tag1'},
                {'db': 'test*2',
                 'message': 'commit 2',
                 'parent': 1,
                 'revision': 2,
                 'tag': 'tag2'},
                {'db': 'test*3',
                 'message': 'commit 3',
                 'parent': 1,
                 'revision': 3,
                 'tag': 'tag3'},
                ]
        output = odb._glog_output(revs)
        expected = [
            'o |\t3: commit 3',
            '| |',
            '| |',
            '| o\t2: commit 2',
            '| |',
            '|/',
            'o\t1: commit 1']
        self.assertEqual(expected, output)
        revs = [{'db': 'test*1',
                 'message': 'commit 1',
                 'parent': 0,
                 'revision': 1, },
                {'db': 'test*3',
                 'message': 'commit 3',
                 'parent': 2,
                 'revision': 3, },
                {'db': 'test*4',
                 'message': 'commit 4',
                 'parent': 3,
                 'revision': 4, },
                ]
        output = odb._glog_output(revs)
        expected = [
            '| o\t4: commit 4',
            '| |',
            '| |',
            '| o\t3: commit 3',
            '|',
            '|',
            'o\t1: commit 1']
        self.assertEqual(expected, output)
        revs = [{'db': 'test*1',
                 'message': 'commit 1',
                 'parent': 0,
                 'revision': 1, },
                {'db': 'test*3',
                 'message': 'commit 3\n',
                 'parent': 2,
                 'revision': 3, },
                {'db': 'test*4',
                 'message': 'commit 4',
                 'parent': 1,
                 'revision': 4, },
                ]
        output = odb._glog_output(revs)
        expected = [
            'o |\t4: commit 4',
            '| |',
            '| |',
            '| o\t3: commit 3',
            '|',
            '|',
            'o\t1: commit 1']
        self.assertEqual(expected, output)
        revs = [{'db': 'test*1',
                 'message': 'commit 1',
                 'parent': 0,
                 'revision': 1,
                 'tag': 'tag1'},
                {'db': 'test*2',
                 'message': 'commit 2',
                 'parent': 1,
                 'revision': 2, },
                {'db': 'test*3',
                 'message': 'commit 3',
                 'revision': 3,
                 'parent': 2, },
                {'db': 'test*4',
                 'message': 'commit 4',
                 'revision': 4,
                 'parent': 1,
                 'tag': 'tag4'},
                {'db': 'test*5',
                 'message': 'commit 5',
                 'revision': 5,
                 'parent': 4, },
                {'db': 'test*6',
                 'message': 'commit 6',
                 'revision': 6,
                 'parent': 1, },
                {'db': 'test*7',
                 'message': 'commit 7',
                 'revision': 7,
                 'parent': 1, },
                {'db': 'test*8',
                 'message': 'commit 8',
                 'revision': 8,
                 'parent': 7, },
                {'db': 'test*9',
                 'message': 'commit 9',
                 'revision': 9,
                 'parent': 1, },
                {'db': 'test*10',
                 'message': 'commit 10',
                 'revision': 10,
                 'parent': 7, },
                ]
        output = odb._glog_output(revs)
        expected = [
            '| o | | | |\t10: commit 10',
            '| | | | | |',
            '| | | | | |',
            'o | | | | |\t9: commit 9',
            '| | | | | |',
            '| | | | | |',
            '| | o | | |\t8: commit 8',
            '| | | | | |',
            '| |/ / / /',
            '| o | | |\t7: commit 7',
            '| | | | |',
            '| | | | |',
            '| | o | |\t6: commit 6',
            '| | | | |',
            '| | | | |',
            '| | | o |\t5: commit 5',
            '| | | | |',
            '| | | | |',
            '| | | o |\t4: commit 4',
            '| | | | |',
            '| | | | |',
            '| | | | o\t3: commit 3',
            '| | | | |',
            '| | | | |',
            '| | | | o\t2: commit 2',
            '| / / / /',
            '|/ / / /',
            '| / / /',
            '|/ / /',
            '| / /',
            '|/ /',
            '| /',
            '|/',
            'o\t1: commit 1', ]
        self.assertEqual(expected, output)

    def tearDown(self):
        """ cleanup
        """
        # drop everything (even if tests failed)
        odb = ODB(self.db)
        odb.purge('all', confirm=True)
        odb.dropdb()
