from setuptools import setup, find_packages

setup(
    name='Expedition',
    version='0.1.0',
    author='Tom Cheney',
    author_email='tom@ttcmarine.com',
    description='Python wrapper for the Expedition DLL',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/TTCMarine/Expedition-Python',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.12',
    ],
)