#!/usr/bin/env python
"""
Setup script for the Indian Bank Reconciliation System.
"""

from setuptools import setup, find_packages

# Core dependencies
core_dependencies = [
    'pandas>=2.0.0',
    'numpy>=1.24.0',
    'python-dateutil>=2.8.2',
    'openpyxl>=3.1.0',
    'xlrd>=2.0.1',
    'fuzzywuzzy>=0.18.0',
    'python-Levenshtein>=0.21.0',
    'pyyaml>=6.0.0',
]

# OCR dependencies
ocr_dependencies = [
    'pytesseract>=0.3.10',
    'pdf2image>=1.16.3',
    'opencv-python>=4.8.0',
    'Pillow>=10.0.0',
]

# Email dependencies
email_dependencies = [
    'secure-smtplib>=0.1.1',
    'python-dotenv>=1.0.0',
    'email-validator>=2.0.0',
    'beautifulsoup4>=4.12.2',
]

# Combine all dependencies
all_dependencies = core_dependencies + ocr_dependencies + email_dependencies

# Basic setup configuration
setup_args = {
    'name': 'indian-bank-recon',
    'version': '0.2.0',
    'description': 'Comprehensive reconciliation system for Indian bank statements with OCR and email integration',
    'author': 'Aditya',
    'author_email': 'example@example.com',
    'url': 'https://github.com/username/indian-bank-recon',
    'packages': find_packages(),
    'include_package_data': True,
    'install_requires': all_dependencies,
    'entry_points': {
        'console_scripts': [
            'bank-recon=bank_recon.cli:main',
        ],
    },
    'python_requires': '>=3.8',
}

# Read README for long description
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        setup_args['long_description'] = f.read()
        setup_args['long_description_content_type'] = 'text/markdown'
except (IOError, OSError):
    pass  # Skip if README.md is not accessible

# Run setup with our args
setup(**setup_args)