from setuptools import setup, find_packages

setup(
    name="data-platform-analytics",
    version="1.0.0",
    packages=find_packages(where=".", include=["src*"]),
    python_requires=">=3.11",
    install_requires=[
        "duckdb>=0.10.0",
        "fastapi>=0.110.0",
        "strawberry-graphql[fastapi]>=0.220.0",
        "uvicorn[standard]>=0.27.0",
    ],
)
