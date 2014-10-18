import psycopg2
from psycopg2.extensions import AsIs


class TagExists(Exception):
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
                self.set('revision', revision, cr)
                self.set('parent', '0', cr)
        return int(revision)

    def set(self, key, value, cr=None):
        """ set the value of a key
        """
        update = "UPDATE ir_config_parameter SET value=%s WHERE key=%s"
        insert = "INSERT INTO ir_config_parameter (value, key) values (%s, %s)"
        values = (str(value), 'odb.%s' % key)
        if cr is not None:
            cr.execute(update, values)
            if not cr.rowcount:
                cr.execute(insert, values)
        else:
            with self.connect() as cn, cn.cursor() as cr:
                cr.execute(update, values)
                if not cr.rowcount:
                    cr.execute(insert, values)

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

    def rem(self, key, cr=None):
        """ delete a key
        """
        req = "DELETE FROM ir_config_parameter WHERE key=%s"
        if cr is not None:
            cr.execute(req, ('odb.' + key,))
        else:
            with self.connect() as cn, cn.cursor() as cr:
                cr.execute(req, ('odb.' + key,))

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

    def commit(self):
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
        self.rem('tag')

    def revert(self, parent=None, tag=None):
        """ drop the current db and start back from this parent
        (or the current parent if no parent is specified)
        """
        if parent is None and tag is None:  # revert to last
            parent = self.parent()
        if tag:  # revert to tag
            tagfound = [r for r in self.log() if r.get('tag') == tag]
            if tagfound:
                parent = tagfound[0]['revision']
            else:
                return
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
        self.rem('tag')

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
                    'revision': int(self.get('revision', cr)),
                    'parent': int(self.get('parent', cr)),
                })
                tag = self.get('tag', cr)
                if tag:
                    log[-1]['tag'] = tag
        return sorted(log, key=lambda x: x['revision'], reverse=True)

    def purge(self, what, confirm=False):
        """ purge the revisions
        what can be: 'all'
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

    def tag(self, tag=None, revision=None, delete=False):
        """ tag a specific revision or the current one by default
        """
        tags = [r for r in self.log() if 'tag' in r]
        if delete:
            if tag in [r.get('tag') for r in tags]:
                db = [r['db'] for r in tags if r.get('tag') == tag][0]
                with self.connect(db) as cn, cn.cursor() as cr:
                    return self.rem('tag', cr)
            return
        if tag is None and revision is None:
            return tags
        if tag is not None and tag in [r.get('tag') for r in tags]:
            raise TagExists('This tag already exists')
        if revision is None:
            revision = self.revision()
        if self.revision() == revision:
            db = self.db
        else:
            db = '%s*%s' % (self.db, revision)
        with self.connect(db) as cn, cn.cursor() as cr:
            self.set('tag', tag, cr)
