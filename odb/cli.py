import os
import argparse
from .odb import ODB, TagExists
CONF = os.path.expanduser('~/.anybox.pg.odoo')


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
    parser_purge = subparsers.add_parser('purge', help="Destroy revisions")
    parser_purge.add_argument('what', choices=['all'],
                              help='all: destroy all revisions except the current db')
    parser_purge.add_argument('-y', '--yes', action='store_true', help='Destroy without asking')
    parser_tags = subparsers.add_parser('tags', help="List all tags")
    parser_tag = subparsers.add_parser('tag', help="Tag a specific revision")
    parser_tag.add_argument('-d', '--delete', action='store_true', help='Delete tag')
    parser_tag.add_argument('tag', help='Tag')
    parser_tag.add_argument('revision', metavar='revision', nargs='?', help='Revision')

    def init(args):
        odb = ODB(args.db[0])
        odb.init()
        open(CONF, 'w').write(odb.db)
        print('Now revision %s' % odb.revision())

    def commit(args):
        odb = ODB(open(CONF).read())
        odb.commit()
        print('Now revision %s' % odb.revision())

    def revert(args):
        odb = ODB(open(CONF).read())
        if args.revision and args.revision.isdigit():
            odb.revert(parent=args.revision)
        elif args.revision and args.revision.isalnum():
            odb.revert(tag=args.revision)
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
            if 'tag' in logitem:
                print '\ttag: %s' % logitem['tag']

    def purge(args):
        odb = ODB(open(CONF).read())
        try:
            to_purge = odb.purge(args.what, args.yes)
        except NotImplementedError:
            print 'Unkown purge command'
            return
        print('Dropping these databases: %s' % ', '.join([i['db'] for i in to_purge]))
        if args.yes or raw_input('Confirm? y[N] ').lower() == 'y':
            odb.purge(args.what, True)
            print 'Purged'
        else:
            print 'Cancelled'

    def tags(args):
        odb = ODB(open(CONF).read())
        tags = odb.tag()
        for item in tags:
            print '%(tag)s (%(db)s)' % item

    def tag(args):
        odb = ODB(open(CONF).read())
        if args.delete:
            return odb.tag(args.tag, delete=True)
        try:
            odb.tag(args.tag, args.revision)
        except TagExists:
            print 'This tag already exists'

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
    args.func(args)
