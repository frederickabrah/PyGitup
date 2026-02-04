from setuptools import setup, find_packages

setup(
    name='pygitup',
    version='2.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests',
        'PyYAML',
        'tqdm',
        'pip-audit',
        'inquirer',
        'rich',
        'beautifulsoup4',
        'pytest' # For development/testing purposes
    ],
    entry_points={
        'console_scripts': [
            'pygitup=pygitup.main:main',
        ],
    },
    author='Frederick Abraham',
    author_email='frederickabraham547@gmail.com',
    description='A CLI tool to simplify and automate GitHub workflows.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/frederickabrah/PyGitUp',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
