from setuptools import setup, find_packages
setup(
    name="anybox.pg.odoo",
    version="0.5",
    packages=find_packages(),
    install_requires=['psycopg2>=2.5'],
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
    long_description=open('README.rst').read() + open('CHANGES.rst').read(),
    license="GPLv3",
    keywords="postgresql odoo snapshot commit version",
    url="",

    entry_points={
        'console_scripts': [
            'odb=odb.cli:main',
        ],
    },
)
