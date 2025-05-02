import setuptools

with open("README.md", "r") as f:
    readme = f.read()

setuptools.setup(
    name="ncon-torch",
    version="0.2.2",
    author="Faisal Alam",
    author_email="mfalam2@illinois.edu",
    description="Tensor network contraction function with GPU and autograd support via PyTorch.",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/alam-faisal/ncon-torch",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
    ],
    keywords=["tensor networks"],
    install_requires=["numpy>=1.11.0"],
    extras_require={"tests": ["pytest", "coverage", "pytest-cov"]},
    python_requires=">=3.6",
)