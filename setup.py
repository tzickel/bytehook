# -*- coding: utf-8 -*-
from __future__ import with_statement
from setuptools import setup


def get_version():
    with open('bytehook.py') as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])


def get_long_description():
    with open('README.md') as f:
        return f.read()

setup(
    name='bytehook',
    version=get_version(),
    description="Python bytecode hook",
    long_description=get_long_description(),
    keywords='bytehook bytecode hook',
    author='tzickel',
    url='http://github.com/tzickel/bytehook/',
    license='MIT',
    py_modules=['bytehook'],
    namespace_packages=[],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # Broken with Python 3: https://github.com/pypa/pip/issues/650
        # 'setuptools',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Debuggers',
    ],
    test_suite='testsuite.test',
)
