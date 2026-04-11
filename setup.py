from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="hp-tuners-ai-agent",
    version="1.0.0",
    author="wexcomm",
    author_email="wexcomm@users.noreply.github.com",
    description="AI agent for HP Tuners ECU tuning and vehicle diagnostics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wexcomm/hp-tuners-ai-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Automotive",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest>=6.2.0", "pytest-cov>=2.12.0", "black>=21.0.0", "flake8>=3.9.0"],
    },
    entry_points={
        "console_scripts": [
            "hp-tuners-agent=src.cli:main",
        ],
    },
)