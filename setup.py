#!/usr/bin/env python
"""
Setup script for the Indian Bank Reconciliation System.
"""

from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='indian-bank-recon',
    version='0.1.0',
    description='Comprehensive reconciliation system for Indian bank statements',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Aditya',
    author_email='example@example.com',
    url='https://github.com/username/indian-bank-recon',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'python-dateutil>=2.8.2',
        'openpyxl>=3.1.0',
        'xlrd>=2.0.1',
        'fuzzywuzzy>=0.18.0',
        'python-Levenshtein>=0.21.0',
        'pyyaml>=6.0.0',
    ],
    entry_points={
        'console_scripts': [
            'bank-recon=bank_recon.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Office/Business :: Financial :: Accounting',
    ],
    python_requires='>=3.8',
    keywords='bank, reconciliation, accounting, finance, india, banking',
)