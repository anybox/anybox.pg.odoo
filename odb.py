import argparse
import logging
import psycopg2
from psycopg2.extensions import AsIs


class AlreadyInitialized(Exception):
    pass


class NotInitialized(Exception):
    pass


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
            cn.cursor().execute("create database %s", (AsIs(db),))
        with self.connect(db) as cn, cn.cursor() as cr:
            cr.execute("create table ir_config_parameter "
                       "(key character varying(256), value text)")

    def dropdb(self):
        """ drop db
        """
        with self.connect('postgres') as cn:
            cn.autocommit = True
            cn.cursor().execute("drop database %s", (AsIs(self.db),))

    def init(self):
        """ initialize the db with the version
        """
        with self.connect() as cn, cn.cursor() as cr:
            cr.execute("SELECT value FROM ir_config_parameter WHERE key = 'odb.version'")
            version = cr.fetchone()
            if version is None:
                version = '0'
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.version', %s)", version)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.parent', %s)", version)
                cr.execute("INSERT INTO ir_config_parameter "
                           "(key, value) values ('odb.tip', %s)", version)
                return int(version)
            raise AlreadyInitialized('Already initialized')

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
            if len(res) == 1:
                return res[0]
            else:
                raise NotInitialized()

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

    def commit(self):
        """ create a snapshot and change the current version
        """
        curversion = self.version()
        newversion = self.tip() + 1
        self.set('tip', newversion)
        targetdb = '_'.join([self.db.rsplit('_')[0], str(newversion)])
        with self.connect() as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute("SELECT pg_terminate_backend(pg_stat_activity.pid) "
                       "FROM pg_stat_activity "
                       "WHERE pg_stat_activity.datname=%s "
                       "AND pid <> pg_backend_pid();", (self.db,))
            cr.execute("CREATE DATABASE %s WITH TEMPLATE %s", (AsIs(targetdb), AsIs(self.db)))
        # switch to the new db
        self.db = targetdb
        self.set('tip', newversion)
        self.set('version', newversion)
        self.set('parent', curversion)

    def revert(self, version):
        """ drop the current db and start back from this version
        """
        tip = self.tip()
        newversion = tip + 1
        self.set('tip', newversion)
        sourcedb = '_'.join([self.db.rsplit('_')[0], str(version)])
        targetdb = '_'.join([self.db.rsplit('_')[0], str(newversion)])
        with self.connect('postgres') as cn, cn.cursor() as cr:
            cn.autocommit = True
            cr.execute("DROP DATABASE %s", (AsIs(self.db),))
            cr.execute("CREATE DATABASE %s WITH TEMPLATE %s",
                       (AsIs(targetdb), AsIs(sourcedb)))
        self.db = targetdb
        self.set('tip', newversion)
        self.set('version', newversion)
        self.set('parent', version)


def main():
    parser = argparse.ArgumentParser(
        prog="odb",
        description=u"PostgreSQL database snapshotting tool for Odoo",)
    parser.add_argument('-d', '--database', required=True,
                        help='Database to snapshot')

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
