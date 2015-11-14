import os
import sys
try:
    import argparse
except ImportError:  # Python3.1
    print("Please install argparse")
    exit()
try:
    import configparser
except ImportError:  # Python3.1
    from backports import configparser

from .odb import ODB, TagExists, NoTemplate
CONF = os.path.expanduser('~/.anybox.pg.odoo')

get_input = input
if sys.version[0] == '2':
    get_input = raw_input


def main():
    parser = argparse.ArgumentParser(
        prog="odb",
        description="Postgresql snapshot versionning tool (for Odoo)",)
    subparsers = parser.add_subparsers(help='sub-commands')
    parser_init = subparsers.add_parser('init', help='Set the current db')
    parser_init.add_argument('db', metavar='db', nargs=1, help='database name to work on')
    parser_init.add_argument('--user', '-u', metavar='Username', help='db user')
    parser_init.add_argument('--password', '-p', metavar='pass',
                             help='db user password. BE CAREFUL this is saved as clear text'
                                  'in your conf file (%s), prefer using pam users.' % CONF)
    parser_init.add_argument('--host', '-H', metavar='Hostname', help='The DB hostname host')
    parser_init.add_argument('--port', '-P', metavar='Port', help='The DB port to connect on')
    parser_commit = subparsers.add_parser('commit', help='Save the current db in a new revision')
    parser_commit.add_argument('-m', '--message', nargs='?', help='Commit message')
    parser_info = subparsers.add_parser('info', help='Display the revision of the current db')
    parser_revert = subparsers.add_parser(
        'revert', help='Drop the current db and clone from a previous revision')
    parser_revert.add_argument('revision', nargs='?', help='revision to revert to')
    parser_log = subparsers.add_parser('log', help='List all available revisions')
    parser_log.add_argument('--limit', '-l', type=int, metavar='NUM',
                            help="limit number of changes displayed")
    parser_log.add_argument('--graph', '-g', action='store_true',
                            help='display a left graph to highlight history')
    parser_purge = subparsers.add_parser('purge', help="Destroy revisions")
    parser_purge.add_argument('what', choices=['all', 'keeptags'],
                              help='all: destroy all revisions except the current db')
    parser_purge.add_argument('-y', '--yes', action='store_true', help='Destroy without asking')
    parser_tags = subparsers.add_parser('tags', help="List all tags")
    parser_tag = subparsers.add_parser('tag', help="Tag a specific revision")
    parser_tag.add_argument('-d', '--delete', action='store_true', help='Delete tag')
    parser_tag.add_argument('tag', help='Tag')
    parser_tag.add_argument('revision', metavar='revision', nargs='?', help='Revision')

    def odb_from_conf_file(conf_file):
        config = configparser.ConfigParser()
        config.read(conf_file)
        dbname = config.get('database', 'dbname')
        user = config.get('database', 'user', fallback=None)
        password = config.get('database', 'password', fallback=None)
        host = config.get('database', 'host', fallback=None)
        port = config.get('database', 'port', fallback=None)
        return ODB(dbname, user, password=password, host=host, port=port)

    def init(args):
        odb = ODB(args.db[0], user=args.user, password=args.password,
                  host=args.host, port=args.port)
        odb.init()
        config = configparser.ConfigParser()
        config.add_section('database')
        config.set('database', 'dbname', odb.db)
        if odb.user:
            config.set('database', 'user', odb.user)
        if odb.password:
            config.set('database', 'password', odb.password)
        if odb.host:
            config.set('database', 'host', odb.host)
        if odb.port:
            config.set('database', 'port', odb.port)
        with open(CONF, 'w') as configfile:
            config.write(configfile)
        print('Now revision %s' % odb.revision())

    def commit(args):
        odb = odb_from_conf_file(CONF)
        odb.commit(msg=args.message)
        print('Now revision %s' % odb.revision())

    def revert(args):
        odb = odb_from_conf_file(CONF)
        try:
            if args.revision and args.revision.isdigit():
                odb.revert(parent=args.revision)
            elif args.revision and args.revision.isalnum():
                odb.revert(tag=args.revision)
            else:
                odb.revert()
            print('Reverted to parent %s, now at revision %s' % (odb.parent(), odb.revision()))
        except NoTemplate as e:
            print(e.args[0])

    def info(args):
        odb = odb_from_conf_file(CONF)
        print('database: %s' % odb.db)
        if odb.user:
            print('user: %s' % odb.user)
        if odb.host:
            print('host: %s' % odb.host)
        if odb.port:
            print('port: %s' % odb.port)
        print('revision : %s (parent: %s)' % (odb.revision(), odb.parent()))
        tag = odb.get('tag')
        if tag:
            print('tag: %s' % tag)

    def log(args):
        odb = odb_from_conf_file(CONF)
        output = []
        if args.graph:
            output = odb.glog(args.limit)
        else:
            for logitem in odb.log(args.limit):
                output.append('%(db)s:\n\trevision: %(revision)s\n\t'
                              'parent: %(parent)s' % logitem)
                if 'message' in logitem:
                    output.append('\tmessage: %s' % logitem['message'])
                if 'tag' in logitem:
                    output.append('\ttag: %s' % logitem['tag'])
        for line in output:
            print(line)

    def purge(args):
        odb = odb_from_conf_file(CONF)
        try:
            to_purge = odb.purge(args.what, args.yes)
        except NotImplementedError:
            print('Unkown purge command')
            return
        if not to_purge:
            print('Nothing to purge')
            return
        print('Dropping these databases: %s' % ', '.join([i['db'] for i in to_purge]))
        if args.yes or get_input('Confirm? [y/N] ').lower() == 'y':
            odb.purge(args.what, True)
            print('Purged')
        else:
            print('Cancelled')

    def tags(args):
        odb = odb_from_conf_file(CONF)
        tags = odb.tag()
        for item in tags:
            print('%(tag)s (%(db)s)' % item)

    def tag(args):
        odb = odb_from_conf_file(CONF)
        if args.delete:
            return odb.tag(args.tag, delete=True)
        try:
            odb.tag(args.tag, args.revision)
        except TagExists:
            print('This tag already exists')

    parser_init.set_defaults(func=init)
    parser_commit.set_defaults(func=commit)
    parser_info.set_defaults(func=info)
    parser_revert.set_defaults(func=revert)
    parser_info.set_defaults(func=info)
    parser_log.set_defaults(func=log)
    parser_purge.set_defaults(func=purge)
    parser_tags.set_defaults(func=tags)
    parser_tag.set_defaults(func=tag)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
