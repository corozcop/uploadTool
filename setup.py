#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read version from package
def get_version():
    version = {}
    with open("trackandtrace/__init__.py", "r") as f:
        exec(f.read(), version)
    return version["__version__"]

# Read long description from README
def get_long_description():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read requirements
def get_requirements():
    with open("requirements.txt", "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="trackandtrace-upload",
    version=get_version(),
    author="Track and Trace Team",
    author_email="admin@yourcompany.com",
    description="Production-grade email to PostgreSQL ETL service",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/trackandtrace-upload",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Email",
        "Topic :: Database",
        "Topic :: System :: Systems Administration",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "trackandtrace=trackandtrace.main_service:main",
        ],
    },
    include_package_data=True,
    package_data={
        "trackandtrace": [
            "*.py",
        ],
    },
    data_files=[
        ("etc/systemd/system", ["systemd/trackandtrace.service"]),
        ("usr/local/bin", ["deployment/deploy.sh"]),
    ],
    zip_safe=False,
    keywords="email postgresql etl excel automation service daemon",
    project_urls={
        "Documentation": "https://github.com/yourorg/trackandtrace-upload/wiki",
        "Source": "https://github.com/yourorg/trackandtrace-upload",
        "Tracker": "https://github.com/yourorg/trackandtrace-upload/issues",
    },
) 