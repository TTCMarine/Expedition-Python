import re
from setuptools import setup, find_packages

# Read version from Expedition/version.py without importing the module
with open('Expedition/version.py') as f:
    content = f.read()
    version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
    if not version_match:
        raise RuntimeError("Unable to find __version__ in Expedition/version.py")
    version = version_match.group(1)
    
    
setup(
    name='Expedition-Python',
    version=version,
    author='Tom Cheney',
    author_email='tom@ttcmarine.com',
    description='Python wrapper for the Expedition DLL',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/TTCMarine/Expedition-Python',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.12',
    ],
)
