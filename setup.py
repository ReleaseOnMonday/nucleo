"""Setup script for Nucleo."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme = Path(__file__).parent / "README.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="nucleo",
    version="0.1.0",
    description="Ultra-lightweight AI assistant in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Nucleo Contributors",
    url="https://github.com/ReleaseOnMonday/nucleo",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.27.0",
        "anthropic>=0.25.0",
    ],
    extras_require={
        "telegram": ["python-telegram-bot>=20.0"],
        "discord": ["discord.py>=2.3.0"],
        "search": ["brave-search-python>=0.1.0"],
        "dev": ["pytest>=8.0.0", "ruff>=0.3.0"],
    },
    entry_points={
        "console_scripts": [
            "nucleo=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
