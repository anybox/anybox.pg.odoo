from setuptools import setup, find_packages
setup(
    name="anybox.pg.odoo",
    version="0.1",
    packages=find_packages(),
    install_requires=['psycopg2>=2.5'],
    test_suite='test',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
    ],


    # metadata for upload to PyPI
    author="Christophe Combelles",
    author_email="ccomb@anybox.fr",
    description="Database snapshotting tool for PostgreSQL",
    long_description=open('README.rst').read(),
    license="GPLv3",
    keywords="postgresql odoo snapshot commit",
    url="",

    entry_points={
        'console_scripts': [
            'odb=odb:main',
        ],
    },
)
