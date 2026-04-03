import os, re
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

with open(os.path.join("ecclesia", "__init__.py")) as f:
    content = f.read()
version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
if version_match:
    version = version_match.group(1)
else:
    raise RuntimeError("Unable to find version string.")

setup(
    name="ecclesia",
    version=version,
    description="General App",
    author="Kunle Oduntan",
    author_email="kunleoduntan@gmail.com",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)