import json
import os
import shutil
from typing import List

import cv2
import numpy as np
import numpy.typing as npt
import ruamel.yaml as yaml


def read_image(filename: str, dtype: npt.DTypeLike='uint8') -> np.ndarray:
    ''' Generically read an image using CV2

    Parameters:
    filename (str): path to the image file to read
    dtype (npt.DTypeLike): dtype of the output data

    Returns:
    np.ndarray containing image data
    '''
    image = cv2.imread(filename)
    return image.astype(dtype)


def read_yaml(yaml_file: str) -> dict:
    ''' Read a yaml file into dict object

    Parameters:
    yaml_file (str): path to yaml file

    Returns:
    return_dict (dict): dict of yaml contents
    '''
    with open(yaml_file, 'r') as yfile:
        yml = yaml.YAML(typ='safe')
        return yml.load(yfile)


def write_yaml(yaml_file: str, data: dict) -> None:
    ''' Write a dict object into a yaml file

    Parameters:
    yaml_file (str): path to yaml file
    data (dict): dict of data to write to `yaml_file`
    '''
    with open(yaml_file, 'w') as yfile:
        yml = yaml.YAML(typ='safe')
        yml.default_flow_style = False
        yml.dump(data, yfile)


def read_label_config(path: str) -> str:
    ''' Read a label configuration file

    Parameters:
    path (str): path to the file containing a label configuration

    Returns:
    label configuration (str)
    '''
    with open(path, 'r') as label_config:
        return label_config.read()


def read_ls_tasks(path: str) -> List[dict]:
    ''' Read a label studio tasks file (json format)

    Parameters:
    path (str): path to the file containing a label studio tasks in json format

    Returns:
    tasks (List[dict])
    '''
    with open(path, 'r') as task_file:
        return json.load(task_file)


def backup_existing_file(origional_path: str) -> str:
    ''' Backup a file, ensuring no filename clashes

    Given a path, while that path exists, we append an incrementing suffix
    until the path no longer exists on the file system. The file is then
    copied to the new path. The new path is returned.

    Parameters:
    origional_path (str): name of the file that should be backed up

    Returns
    str - new file path
    '''

    counter = 0
    new_path = origional_path
    base, ext = os.path.splitext(origional_path)
    while os.path.exists(new_path):
        counter += 1
        new_path = f'{base}.backup-{counter}{ext}'

    shutil.copy2(origional_path, new_path)
    return new_path
