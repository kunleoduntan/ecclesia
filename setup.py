from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n") if open("requirements.txt").read().strip() else []

setup(
    name="ecclesia",
    version="2.0.0",
    description=(
        "Ecclesia Platform — Telephony, Finance, Payroll, Audit Intelligence, "
        "ESS, Customer & Supplier Self-Service Portals"
    ),
    author="Kunle Oduntan",
    author_email="kunleoduntan@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)