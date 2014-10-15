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

    def dropdb(self):
        """ drop db
        """
        with self.connect('postgres') as cn:
            cn.autocommit = True
            cn.cursor().execute('DROP DATABASE "%s"', (AsIs(self.db),))

    def init(self):
        """ initialize the db with the version
        """
        version = self.get('version')
        with self.connect() as cn, cn.cursor() as cr:
            if version is None:
                version = '1'
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.version', %s)", version)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.parent', %s)", '0')
        return int(version)

    def set(self, key, value):
        """ set the value of a key
        """
        with self.connect() as cn, cn.cursor() as cr:
            cr.execute("UPDATE ir_config_parameter SET value=%s WHERE key=%s",
                       (str(value), 'odb.%s' % key))

    def get(self, key):
        """ get the value of a key
        """
        with self.connect() as cn, cn.cursor() as cr:
            cr.execute("SELECT value FROM ir_config_parameter WHERE key=%s",
                       ('odb.' + key,))
            res = cr.fetchone()
            if res is not None and len(res) == 1:
                return res[0]

    def version(self):
        """ returns the db version
        """
        return int(self.get('version'))

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
        """ create a snapshot and change the current version
        Corresponds to the commit command
        """
        version = self.version()
        targetdb = '*'.join([self.db, str(version)])
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            self._disconnect(cr, self.db)
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(targetdb), AsIs(self.db)))
        self.set('version', version + 1)
        self.set('parent', version)

    def revert(self, parent=None):
        """ drop the current db and start back from this parent
        (or the current parent if no parent is specified)
        """
        if parent is None:
            parent = self.parent()
        # store version because we'll drop
        curversion = self.version()
        sourcedb = '*'.join([self.db, str(parent)])
        with self.connect() as cn, cn.cursor() as cr:
            cn.autocommit = True
            self._disconnect(cr, self.db)
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute('DROP DATABASE "%s"', (AsIs(self.db),))
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(self.db), AsIs(sourcedb)))
        self.set('version', curversion)
        self.set('parent', parent)


def main():
    parser = argparse.ArgumentParser(
        prog="odb",
        description=u"PostgreSQL snapshot versionning tool for Odoo",)
    subparsers = parser.add_subparsers(help='sub-commands')
    parser_init = subparsers.add_parser('init', help='Set the current db')
    parser_init.add_argument(
        'db', metavar='db', nargs=1, help='database to work on')
    parser_commit = subparsers.add_parser(
        'commit', help='Save the current db in a new revision')
    parser_info = subparsers.add_parser(
        'info', help='Display the revision of the current db')
    parser_revert = subparsers.add_parser(
        'revert', help='Drop the current db and clone from a previous revision')
    parser_revert.add_argument('revision', nargs='?', help='revision to revert to')

    def init(args):
        odb = ODB(args.db[0])
        odb.init()
        open(CONF, 'w').write(odb.db)
        print('Now version %s' % odb.version())

    def commit(args):
        odb = ODB(open(CONF).read())
        odb.snapshot()
        print('Now version %s' % odb.version())

    def revert(args):
        odb = ODB(open(CONF).read())
        if args.revision:
            odb.revert(args.revision[0])
        else:
            odb.revert()
        print('Reverted to parent %s, now at revision %s' % (odb.parent(), odb.version()))

    def info(args):
        odb = ODB(open(CONF).read())
        print('database: %s' % odb.db)
        print('version : %s (parent: %s)' % (odb.version(), odb.parent()))

    parser_init.set_defaults(func=init)
    parser_commit.set_defaults(func=commit)
    parser_info.set_defaults(func=info)
    parser_revert.set_defaults(func=revert)

    args = parser.parse_args()
    args.func(args)
