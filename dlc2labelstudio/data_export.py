import math
import os
from typing import Dict, List, Optional, Union

import pandas as pd

from dlc2labelstudio.io import backup_existing_file
from dlc2labelstudio.ls_annot_parser import read_annotations


def convert_ls_annot_to_dlc(ls_annotations: List[dict], dlc_config: dict, split: bool=True, save: bool=True) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    ''' Given a list of label studio annotation, convert into DLC annotations format.

    If split is true, annotations will be subset by their origin video. Otherwise all annotations will be saved in the project
    root directory. Split also affects the behavior of `save`.

    Parameters:
    ls_annotations (List[dict]): annotations in label studio format
    dlc_config (dict): configuration data for DLC project
    split (bool): If true, split annotations per video.
    save (bool): If true, results will be persisted to disk in the appropriate locations

    Returns:
    Union[pd.DataFrame, Dict[str, pd.DataFrame]]: If split is True, will return a dict with string keys of the video name and keys
    as a Dataframe containing annotation data. If split is False, will return a DataFrame with all annotation data.
    '''
    data = read_annotations(ls_annotations)#keypoint_names=dlc_config['bodyparts']

    if split:
        grouped = split_annotations_by_directory(data)
        grouped_dlc = {}
        for group, group_data in grouped.items():
            dlc_df = intermediate_annotations_to_dlc(group_data, dlc_config)
            grouped_dlc[group] = dlc_df
            save_dlc_annots(dlc_df, dlc_config, group)
        return grouped_dlc
    else:
        dlc_df = intermediate_annotations_to_dlc(data, dlc_config)
        save_dlc_annots(dlc_df, dlc_config)
        return dlc_df


def save_dlc_annots(annotations: pd.DataFrame, dlc_config: dict, group: Optional[str]=None):
    ''' Save a DataFrame of annotation data a la DLC.

    If files already exist, they will first be backed up.

    Parameters:
    annotations (pd.DataFrame): pandas dataframe of DLC annotation data
    dlc_config (dict): DLC project configuration data
    group (str|None): Optional subdirectory to save results
    '''
    dest = os.path.join(dlc_config['project_path'], 'labeled-data')
    if group is not None:
        dest = os.path.join(dest, group)
    dest = os.path.join(dest, f"CollectedData_{dlc_config['scorer']}")


    csv_dest = dest + '.csv'
    if os.path.exists(csv_dest):
        print(f'WARNING: file already exists! {csv_dest}')
        backup = backup_existing_file(csv_dest)
        print(f' -> Backing this file up to {backup}')

    annotations.to_csv(csv_dest)


    h5_dest = dest + '.h5'
    if os.path.exists(h5_dest):
        print(f'WARNING: file already exists! {h5_dest}')
        backup = backup_existing_file(h5_dest)
        print(f' -> Backing this file up to {backup}')

    annotations.to_hdf(
        h5_dest,
        "df_with_missing",
        format="table",
        mode="w"
    )


def intermediate_annotations_to_dlc(intermediate_annotations: List[dict], dlc_config: dict) -> pd.DataFrame:
    ''' Convert "intermediate-style" annotations to DLC-style DataFrame

    Parameters:
    intermediate_annotations (List[dict]): "intermediate-style" annotations
    dlc_config (dict): DLC project configuration data

    Returns:
    pd.DataFrame - dataframe of annotation data in DLC format
    '''
    col_idx = pd.MultiIndex.from_product(
        [
            [dlc_config['scorer']],
            dlc_config['bodyparts'],
            ['x', 'y']
        ],
        names=['scorer', 'bodyparts', 'coords'])
    row_idx = []
    dlc_data = []

    for itm in intermediate_annotations:
        row_idx.append(itm['file_name'])
        kpts = itm['annotations'][0]['keypoints']

        row_data = []
        for bp in dlc_config['bodyparts']:
            if bp in kpts:
                row_data.extend([
                    kpts[bp]['x'],
                    kpts[bp]['y'],
                ])
            else:
                row_data.extend([math.nan, math.nan])
        dlc_data.append(row_data)
    dlc_df = pd.DataFrame(dlc_data, index=row_idx, columns=col_idx)

    return dlc_df


def split_annotations_by_directory(intermediate_annotations: List[dict]) -> Dict[str, List[dict]]:
    ''' Split annotations into groups according to their file name

    Parameters:
    intermediate_annotations (List[dict]): "intermediate-style" annotations

    Returns:
    Dict[str, List[dict]] - grouped annotations with group as string keys and list of annotations as values
    '''
    grouped = {}

    for annot in intermediate_annotations:
        group = annot['file_name'].split(os.sep)[1]
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(annot)

    return grouped
