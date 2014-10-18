import os
import argparse
import psycopg2
from psycopg2.extensions import AsIs
CONF = os.path.expanduser('~/.anybox.pg.odoo')


class ODB(object):
    """class representing an Odoo instance
    """
    def __init__(self, db=None):
        self.db = db

    def connect(self, db=None):
        """ connect to the current db unless specified
        """
        if db is None:
            db = self.db
        return psycopg2.connect('dbname=%s' % db)

    def createdb(self):
        """ createdb used for tests
        """
        db = self.db
        with self.connect('postgres') as cn:
            cn.autocommit = True
            cn.cursor().execute('CREATE DATABASE "%s"', (AsIs(db),))
        with self.connect(db) as cn, cn.cursor() as cr:
            cr.execute("CREATE TABLE ir_config_parameter "
                       "(key character varying(256), value text)")

    def dropdb(self, db=None):
        """ drop db
        """
        if db is None:
            db = self.db
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            self._disconnect(cr, db)
            cn.cursor().execute('DROP DATABASE "%s"', (AsIs(db),))

    def init(self):
        """ initialize the db with the revision
        """
        revision = self.get('revision')
        with self.connect() as cn, cn.cursor() as cr:
            if revision is None:
                revision = '1'
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.revision', %s)", revision)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.parent', %s)", '0')
        return int(revision)

    def set(self, key, value, cr=None):
        """ set the value of a key
        """
        req = "UPDATE ir_config_parameter SET value=%s WHERE key=%s"
        if cr is not None:
            cr.execute(req, (str(value), 'odb.%s' % key))
        else:
            with self.connect() as cn, cn.cursor() as cr:
                cr.execute(req, (str(value), 'odb.%s' % key))

    def get(self, key, cr=None):
        """ get the value of a key
        """
        req = "SELECT value FROM ir_config_parameter WHERE key=%s"
        if cr is not None:
            cr.execute(req, ('odb.' + key,))
            res = cr.fetchone()
        else:
            with self.connect() as cn, cn.cursor() as cr:
                cr.execute(req, ('odb.' + key,))
                res = cr.fetchone()
        if res is not None and len(res) == 1:
            return res[0]

    def revision(self):
        """ returns the db revision
        """
        return int(self.get('revision'))

    def parent(self):
        """ get the parent snapshot
        """
        return int(self.get('parent'))

    def _disconnect(self, cr, db):
        """ kill all pg connections
        """
        cr.execute("SELECT pg_terminate_backend(pg_stat_activity.pid) "
                   "FROM pg_stat_activity "
                   "WHERE pg_stat_activity.datname=%s "
                   "AND pid <> pg_backend_pid();", (db,))

    def snapshot(self):
        """ create a snapshot and change the current revision
        Corresponds to the commit command
        """
        revision = self.revision()
        targetdb = '*'.join([self.db, str(revision)])
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            self._disconnect(cr, self.db)
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(targetdb), AsIs(self.db)))
        self.set('revision', revision + 1)
        self.set('parent', revision)

    def revert(self, parent=None):
        """ drop the current db and start back from this parent
        (or the current parent if no parent is specified)
        """
        if parent is None:
            parent = self.parent()
        # store revision because we'll drop
        currevision = self.revision()
        sourcedb = '*'.join([self.db, str(parent)])
        with self.connect() as cn, cn.cursor() as cr:
            cn.autocommit = True
            self._disconnect(cr, self.db)
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute('DROP DATABASE "%s"', (AsIs(self.db),))
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(self.db), AsIs(sourcedb)))
        self.set('revision', currevision)
        self.set('parent', parent)

    def log(self):
        """ return a list of previous revisions, each revision being a dict with needed infos
        """
        log = []
        with self.connect() as cn, cn.cursor() as cr:
            req = 'SELECT datname FROM pg_catalog.pg_database WHERE datname like %s'
            cr.execute(req, (self.db + '*%',))
            dbnames = cr.fetchall()
        for db in [d[0] for d in dbnames] + [self.db]:
            with self.connect(db) as cn, cn.cursor() as cr:
                log.append({
                    'db': db,
                    'revision': self.get('revision', cr),
                    'parent': self.get('parent', cr),
                })
        return sorted(log, key=lambda x: x['revision'], reverse=True)

    def purge(self, what, confirm=True):
        """ purge the revisions
        """
        # first get what will be purged, then confirm
        to_purge = [l for l in self.log() if l['db'] != self.db]
        if what == 'all':
            pass
        else:
            raise NotImplementedError('Bad purge command')
        if confirm:
            for logitem in to_purge:
                self.dropdb(logitem['db'])
        return to_purge


def main():
    parser = argparse.ArgumentParser(
        prog="odb",
        description=u"Postgresql snapshot versionning tool (for Odoo)",)
    subparsers = parser.add_subparsers(help='sub-commands')
    parser_init = subparsers.add_parser('init', help='Set the current db')
    parser_init.add_argument('db', metavar='db', nargs=1, help='database to work on')
    parser_commit = subparsers.add_parser('commit', help='Save the current db in a new revision')
    parser_info = subparsers.add_parser('info', help='Display the revision of the current db')
    parser_revert = subparsers.add_parser(
        'revert', help='Drop the current db and clone from a previous revision')
    parser_revert.add_argument('revision', nargs='?', help='revision to revert to')
    parser_log = subparsers.add_parser('log', help='List all available revisions')
    parser_purge = subparsers.add_parser(
        'purge', help="Destroy revisions")
    parser_purge.add_argument('what', choices=['all'],
                              help='all: destroy all revisions except the current db')
    parser_purge.add_argument('-y', '--yes', type=bool, help='Destroy without asking')

    def init(args):
        odb = ODB(args.db[0])
        odb.init()
        open(CONF, 'w').write(odb.db)
        print('Now revision %s' % odb.revision())

    def commit(args):
        odb = ODB(open(CONF).read())
        odb.snapshot()
        print('Now revision %s' % odb.revision())

    def revert(args):
        odb = ODB(open(CONF).read())
        if args.revision:
            odb.revert(args.revision[0])
        else:
            odb.revert()
        print('Reverted to parent %s, now at revision %s' % (odb.parent(), odb.revision()))

    def info(args):
        odb = ODB(open(CONF).read())
        print('database: %s' % odb.db)
        print('revision : %s (parent: %s)' % (odb.revision(), odb.parent()))

    def log(args):
        odb = ODB(open(CONF).read())
        for logitem in odb.log():
            print '%(db)s:\n\trevision: %(revision)s\n\tparent: %(parent)s' % logitem

    def purge(args):
        odb = ODB(open(CONF).read())
        try:
            to_purge = odb.purge(args.what, args.yes)
        except NotImplementedError:
            print 'Unkown purge command'
            return
        print('About to drop all these databases: %s' % ', '.join([i['db'] for i in to_purge]))
        if raw_input('Confirm? y[N] ').lower() == 'y' or args.yes:
            odb.purge(args.what, True)
            print 'Purged'
        else:
            print 'Cancelled'

    parser_init.set_defaults(func=init)
    parser_commit.set_defaults(func=commit)
    parser_info.set_defaults(func=info)
    parser_revert.set_defaults(func=revert)
    parser_info.set_defaults(func=info)
    parser_log.set_defaults(func=log)
    parser_purge.set_defaults(func=purge)

    args = parser.parse_args()
    args.func(args)
