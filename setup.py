from setuptools import setup, find_packages
setup(
    name="anybox.pg.odoo",
    version="0.2",
    packages=find_packages(),
    install_requires=['psycopg2>=2.5'],
    test_suite='odb.test',
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
    description="PostgreSQL database snapshot versionning tool",
    long_description=open('README.rst').read() + open('CHANGES.rst').read(),
    license="GPLv3",
    keywords="postgresql odoo snapshot commit version",
    url="",

    entry_points={
        'console_scripts': [
            'odb=odb.odb:main',
        ],
    },
)
