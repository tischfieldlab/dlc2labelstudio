from setuptools import find_packages, setup


setup(
    name='dlc2labelstudio',
    author='Tischfield Lab',
    description='Connect DLC labeling tasks to Label Studio',
    version='0.1.0',
    license='MIT License',
    install_requires=[
        'click',
        'click-option-group',
        'h5py',
        'label-studio-sdk',
        'numpy',
        'opencv-python'
        'pandas',
        'ruamel.yaml',
        'seaborn',
        'tables==3.6.1',
        'tqdm',
    ],
    extras_require={
        'dev': [
            'pytest',
            'pytest-pep8',
            'pytest-cov',
            'lxml-stubs'
        ]
    },
    python_requires='>=3.8',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'dlc2ls = dlc2labelstudio.cli:cli',
            'dlc2labelstudio = dlc2labelstudio.cli:cli'
        ],
    }
)
