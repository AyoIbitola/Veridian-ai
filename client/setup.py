from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="veridian_client",
    version="0.1.3",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0"
    ],
    author="Veridian AI",
    description="Client SDK for Veridian AI Safety Platform",
    long_description=long_description,
    long_description_content_type='text/markdown',
)
