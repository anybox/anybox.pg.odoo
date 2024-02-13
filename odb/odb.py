import psycopg2
from psycopg2.extensions import AsIs


class TagExists(Exception):
    pass


class NoTemplate(Exception):
    pass


class ODB(object):
    """class representing an Odoo instance
    """
    def __init__(self, db=None, user=None, password=None, host=None, port=None):
        self.db = db
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def connect(self, db=None, user=None, password=None, host=None, port=None):
        """ connect to the current db unless specified
        """
        return psycopg2.connect(
            self._get_connection_string(db, user, password, host, port),)

    def _get_connection_string(self, db=None, user=None, password=None, host=None, port=None):
        """ Create connection string to use to connect to postgresql
        """
        db = self.db if db is None else db
        user = self.user if user is None else user
        password = self.password if password is None else password
        host = self.host if host is None else host
        port = self.port if port is None else port

        connection_string = 'dbname=%s' % db
        if user:
            connection_string += ' user=%s' % user
        if password:
            connection_string += ' password=%s' % password
        if host:
            connection_string += ' host=%s' % host
        if port:
            connection_string += ' port=%s' % port
        return connection_string

    def _createdb(self):
        """ createdb used for tests
        """
        db = self.db
        cn = self.connect('postgres')
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
        cn = self.connect('postgres')
        cn.autocommit = True
        with cn.cursor() as cr:
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
        pid = "pid"
        if cr.connection.server_version < 90200:
            pid = 'procpid'
        cr.execute("SELECT pg_terminate_backend(pg_stat_activity.%s) "
                   "FROM pg_stat_activity "
                   "WHERE pg_stat_activity.datname=%%s "
                   "AND %s <> pg_backend_pid()" % (pid, pid), (db,))

    def commit(self, msg=None):
        """ create a snapshot and change the current revision
        """
        if msg:
            self.set('message', msg)
        revision = self.revision()
        targetdb = '*'.join([self.db, str(revision)])
        cn = self.connect('postgres')
        cn.autocommit = True
        with cn.cursor() as cr:
            self._disconnect(cr, self.db)
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(targetdb), AsIs(self.db)))
        self.set('revision', revision + 1)
        self.set('parent', revision)
        self.rem('tag')
        self.rem('message')

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
        cn = self.connect()
        cn.autocommit = True
        with cn.cursor() as cr:
            self._disconnect(cr, self.db)
        cn = self.connect('postgres')
        cn.autocommit = True
        with cn.cursor() as cr:
            # check that the source db exists to avoid dropping too early
            cr.execute('SELECT count(*) FROM pg_catalog.pg_database where datname=%s', (sourcedb,))
            if not cr.fetchone()[0]:
                raise NoTemplate('Cannot revert because the source db does not exist')
            cr.execute('DROP DATABASE "%s"', (AsIs(self.db),))
            self._disconnect(cr, sourcedb)
            cr.execute('CREATE DATABASE "%s" WITH TEMPLATE "%s"', (AsIs(self.db), AsIs(sourcedb)))
        self.set('revision', currevision)
        self.set('parent', parent)
        self.rem('tag')
        self.rem('message')

    def log(self, limit=None, reversed=True):
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
                msg = self.get('message', cr)
                if msg:
                    log[-1]['message'] = msg
        revs = sorted(log, key=lambda x: x['revision'], reverse=reversed)
        if limit:
            if reversed:
                revs = revs[:limit]
            else:
                if len(revs) > limit:
                    revs = revs[len(revs) - limit:]
        return revs

    def glog(self, limit):
        return self._glog_output(self.log(limit, reversed=False))

    def _nb_interval(self, children_count):
        interval = (children_count - 1) * 2
        return interval if interval > 0 else 2

    def _glog_output(self, revs):
        dag = {}
        output = []
        branches = []
        for rev in revs:
            dag[rev['revision']] = {'children': [],
                                    'parent': [rev['parent']]}
            if dag.get(rev['parent'], False):
                dag[rev['parent']]['children'].append(rev['revision'])
        branches += [revs[0]['revision']]
        for rev in revs:
            new_branche = True
            if rev['revision'] in branches:
                new_branche = False
                index = branches.index(rev['revision'])
            else:
                index = len(branches)
            graph = '| ' * index + 'o ' + '| ' * (len(branches) - 1 - index)
            # if dag.get(dag[rev_id].get())
            output.append("%s\t%s: %s" %
                          (graph.strip(), rev['revision'],
                           rev.get('message', '').strip()))
            from_b = len(branches)
            children_count = len(dag[rev['revision']]['children'])
            interval = self._nb_interval(children_count)
            for child in dag[rev['revision']]['children']:
                branches.insert(index, child)
            if len(dag[rev['revision']]['children']) == 0 and new_branche:
                branches += [rev['revision']]
            if children_count > 0 and not new_branche:
                branches.remove(rev['revision'])
            to_b = len(branches)
            j = 0
            if rev != revs[-1]:
                for i in range(interval):
                    if i % 2:
                        j += 1
                    if children_count > 1 and interval % 2 == 0:
                        output += [('| ' * index + '|/ ' + '/ ' * (
                            from_b + j - 1 - index)).strip()]
                    elif children_count > 2 and interval % 2 != 0:
                        output += [('| ' * index + '| / ' + '/ ' * (
                            from_b + j - 2 - index)).strip()]
                    else:
                        output += [('| ' * to_b).strip()]
                    interval -= 1
        output.reverse()
        return output

    def purge(self, what, confirm=False):
        """ purge the revisions
        ``what`` can be::
        - ``all``: drop all revisions
        - ``keeptags``: drop all untagged revisions
        """
        # first get what will be purged, then confirm
        to_purge = [i for i in self.log() if i['db'] != self.db]
        if what == 'all':
            pass
        elif what == 'keeptags':
            to_purge = [i for i in to_purge if 'tag' not in i]
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
