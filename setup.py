from setuptools import setup, find_packages

setup(
    name='agentops',
    version='{{VERSION_PLACEHOLDER}}',
    author='Alex Reibman',
    author_email='areibman@gmail.com',
    packages=find_packages(),
    install_requires=[
        'requests'
    ],
    extras_require={
        'dev': [
            'pytest',
            'requests_mock'
        ],
    },
)
