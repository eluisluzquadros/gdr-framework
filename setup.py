"""
Setup script for GDR Framework V3.1 Enterprise
"""

from setuptools import setup, find_packages
from pathlib import Path

# Ler README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Ler requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)

setup(
    name='gdr-framework',
    version='3.1.0',
    author='GDR Team',
    author_email='team@gdr-framework.com',
    description='Sistema completo de enriquecimento e qualificação automatizada de leads',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/seu-usuario/gdr-framework',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Business',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Office/Business',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=8.0.0',
            'pytest-asyncio>=0.23.0',
            'pytest-cov>=5.0.0',
            'black>=24.0.0',
            'flake8>=7.0.0',
            'mypy>=1.8.0',
        ],
        'selenium': [
            'selenium>=4.15.0',
            'webdriver-manager>=4.0.0',
        ],
        'nlp': [
            'spacy>=3.7.0',
            'textblob>=0.18.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'gdr-test=src.run_test:main',
            'gdr-pipeline=src.run_complete_pipeline:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.txt', '*.md', '*.yaml', '*.json'],
    },
    zip_safe=False,
)