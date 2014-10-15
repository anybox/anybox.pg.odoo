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
                version = '0'
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.version', %s)", version)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.parent', %s)", version)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.tip', %s)", version)
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

    def tip(self):
        """ get the latest version
        """
        return int(self.get('tip'))

    def snapshot(self):
        """ create a snapshot and change the current version
        Corresponds to the commit command
        """
        curversion = self.version()
        newversion = self.tip() + 1
        self.set('tip', newversion)
        targetdb = '*'.join([self.db.rsplit('*', 1)[0], str(newversion)])
        with self.connect() as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute("SELECT pg_terminate_backend(pg_stat_activity.pid) "
                       "FROM pg_stat_activity "
                       "WHERE pg_stat_activity.datname=%s "
                       "AND pid <> pg_backend_pid();", (self.db,))
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(targetdb), AsIs(self.db)))
        # switch to the new db
        self.db = targetdb
        self.set('tip', newversion)
        self.set('version', newversion)
        self.set('parent', curversion)

    def revert(self, version=None):
        """ drop the current db and start back from this version
        (or the parent if no version is specified)
        """
        if version is None:
            version = self.parent()
        # store version and tip because we'll drop
        curversion = self.version()
        tip = self.tip()
        sourcedb = '*'.join([self.db.rsplit('*', 1)[0], str(version)])
        targetdb = '*'.join([self.db.rsplit('*', 1)[0], str(curversion)])
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute('DROP DATABASE "%s"', (AsIs(self.db),))
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"',
                       (AsIs(targetdb), AsIs(sourcedb)))
        self.db = targetdb
        self.set('tip', tip)
        self.set('version', curversion)
        self.set('parent', version)


def main():
    parser = argparse.ArgumentParser(
        prog="odb",
        description=u"PostgreSQL snapshot versionning tool for Odoo",)
    subparsers = parser.add_subparsers(help='sub-commands')
    parser_init = subparsers.add_parser('init', help='Set the current db')
    parser_init.add_argument(
        'db', metavar='db', nargs=1, help='database to work on')
    parser_commit = subparsers.add_parser(
        'commit', help='Clone the current db to a new revision')
    parser_info = subparsers.add_parser(
        'info', help='Display revision of the current db')
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
        open(CONF, 'w').write(odb.db)

    def revert(args):
        odb = ODB(open(CONF).read())
        parent = odb.parent()
        revision = args.revision[0] if args.revision is not None else parent
        odb.revert(revision)
        print('Reverted to revision %s, now at revision %s' % (parent, odb.version()))
        open(CONF, 'w').write(odb.db)

    def info(args):
        odb = ODB(open(CONF).read())
        print('database: %s' % odb.db)
        print('version : %s (parent: %s, tip: %s)' % (odb.version(), odb.parent(), odb.tip()))

    parser_init.set_defaults(func=init)
    parser_commit.set_defaults(func=commit)
    parser_info.set_defaults(func=info)
    parser_revert.set_defaults(func=revert)

    args = parser.parse_args()
    args.func(args)
