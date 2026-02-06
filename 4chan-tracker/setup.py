from setuptools import setup, find_packages
import os

# Read the contents of README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="py4chantracker",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to track and analyze 4chan threads across multiple boards",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/py4chantracker",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "py4chantracker=py4chantracker.tracker:main",
            "4chantrack=py4chantracker.tracker:main",  # shorter alias
        ],
    },
    keywords="4chan, tracker, monitoring, analytics",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/py4chantracker/issues",
        "Source": "https://github.com/yourusername/py4chantracker",
    },
)
