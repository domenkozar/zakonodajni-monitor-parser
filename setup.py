from setuptools import setup
from setuptools import find_packages

setup(
    name='zakonodajni-monitor-parser',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'click',
        'colorama',
        'requests',
        'redis',
        'lxml',
        'pymongo',
        'structlog',
        'pyquery',
        'toolz',
    ],
    entry_points="""
    [console_scripts]
    zakonodajni-monitor-parser = cli:cli
    """,
    include_package_data=True,
    zip_safe=False,
)
