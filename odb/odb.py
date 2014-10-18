import psycopg2
from psycopg2.extensions import AsIs


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
