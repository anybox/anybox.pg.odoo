import sys
from setuptools import setup, find_packages

requirements = ['psycopg2-binary']
if sys.version_info.major == 2:
    requirements.append('configparser')

setup(
    name="anybox.pg.odoo",
    version="0.7",
    packages=find_packages(),
    install_requires=requirements,
    test_suite='odb.test',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Database',
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],


    # metadata for upload to PyPI
    author="Christophe Combelles",
    author_email="ccomb@anybox.fr",
    description="Postgresql database snapshot versionning tool",
    long_description=open('README.rst').read() + '\n' + open('CHANGES.rst').read(),
    license="GPLv3",
    keywords="odb postgresql odoo snapshot commit version",
    url="",

    entry_points={
        'console_scripts': [
            'odb=odb.cli:main',
        ],
    },
)
