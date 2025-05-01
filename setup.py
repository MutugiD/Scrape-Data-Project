from setuptools import setup, find_packages

setup(
    name='scrape-data-project',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pandas',
        'requests',
        'selenium',
        'beautifulsoup4',
        'webdriver-manager',
        'pytest',
    ],
)