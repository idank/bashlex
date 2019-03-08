try:
    from setuptools import setup  #Py2
except ImportError:
    from distutils.core import setup  #Py3

import sys

install_requires = []
if sys.version_info < (3, 4):
    install_requires.append('enum34')

setup(
    name='bashlex',
    version='0.14',
    url='https://github.com/idank/bashlex.git',
    license='GPLv3+',
    author='Idan Kamara',
    author_email='idankk86@gmail.com',
    description='Python parser for bash',
    long_description='''bashlex is a Python port of the parser used internally by GNU bash.

For the most part it's transliterated from C, the major differences are:

1. it does not execute anything
2. it is reentrant
3. it generates a complete AST

See https://github.com/idank/bashlex/blob/master/README.md for more info.''',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: System Shells',
        'Topic :: Text Processing',
    ],
    install_requires=install_requires,
    packages=['bashlex'],
)
