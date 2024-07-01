from setuptools import setup
from pathlib import Path
from datetime import datetime

#get current file's directory and get requirements.txt path in current file's directory
# current_directory = Path(__file__).parent
# requirements_path = current_directory / 'requirements.txt'
# # Read requirements.txt and use it in setup.py
# def read_requirements():
#     with open(requirements_path, 'r') as req:
#         content = req.read()
#         requirements = content.split('\n')
#     return requirements

# setup(
#     install_requires=read_requirements(),
# )
setup (
    version = f"{datetime.now().strftime('%Y.%m.%d')}c",
)
