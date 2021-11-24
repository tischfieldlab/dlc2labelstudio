import subprocess
import sys

from setuptools import find_packages, setup


def install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

try:
    import cv2  # noqa: F401
except ImportError:
    install('opencv-python')

setup(
    name='dlc2labelstudio',
    author='Tischfield Lab',
    description='Connect DLC labeling tasks to Label Studio',
    version='0.1.0',
    license='MIT License',
    install_requires=[
        'click',
        'h5py',
        'label-studio-sdk',
        'numpy',
        'pandas',
        'ruamel.yaml',
        'seaborn',
        'tables',
        'tqdm',
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-pep8',
            'pytest-cov'
        ]
    },
    python_requires='>=3.6',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['dlc2labelstudio = dlc2labelstudio.cli:cli'],
    }
)
