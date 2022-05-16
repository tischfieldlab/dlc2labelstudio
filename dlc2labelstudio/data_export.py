import itertools
import os
from typing import Dict, List, Optional, Union

import pandas as pd
from dlc2labelstudio.dlc_data import is_multianimal

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
    data = read_annotations(ls_annotations)
    if split:
        grouped = split_annotations_by_directory(data)
        grouped_dlc = {}
        total_errors = 0
        for group, group_data in grouped.items():
            dlc_df, num_errors = intermediate_annotations_to_dlc(group_data, dlc_config)
            total_errors += num_errors
            grouped_dlc[group] = dlc_df

        if total_errors > 0:
            print('Several errors were detected while converting results to DLC format. Please correct the problems and try again!')
            return None

        # wait till we have all data frames, incase an exception, then save
        if save:
            for group, group_df in grouped_dlc.items():
                save_dlc_annots(group_df, dlc_config, group)

        return grouped_dlc
    else:
        dlc_df, num_errors = intermediate_annotations_to_dlc(data, dlc_config)

        if num_errors > 0:
            print('Several errors were detected while converting results to DLC format. Please correct the problems and try again!')
            return None

        if save:
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
        key="df_with_missing",
        format="fixed",
        mode="w"
    )


def make_index_from_dlc_config(dlc_config: dict) -> pd.MultiIndex:
    ''' Given a DLC configuration, prepare a pandas multi-index

    Parameters:
    dlc_config (dict): DLC project configuration data
    '''
    if is_multianimal(dlc_config):
        cols = []
        for individual in dlc_config['individuals']:
            for mabp in dlc_config['multianimalbodyparts']:
                cols.append((dlc_config['scorer'], individual, mabp, 'x'))
                cols.append((dlc_config['scorer'], individual, mabp, 'y'))
        for unbp in dlc_config['uniquebodyparts']:
            cols.append((dlc_config['scorer'], 'single', unbp, 'x'))
            cols.append((dlc_config['scorer'], 'single', unbp, 'y'))

        return pd.MultiIndex.from_tuples(cols, names=('scorer', 'individuals', 'bodyparts', 'coords'))

    else:
        return pd.MultiIndex.from_product(
            [
                [dlc_config['scorer']],
                dlc_config['bodyparts'],
                ['x', 'y']
            ],
            names=['scorer', 'bodyparts', 'coords'])



def intermediate_annotations_to_dlc(intermediate_annotations: List[dict], dlc_config: dict) -> pd.DataFrame:
    ''' Convert "intermediate-style" annotations to DLC-style DataFrame

    Parameters:
    intermediate_annotations (List[dict]): "intermediate-style" annotations
    dlc_config (dict): DLC project configuration data

    Returns:
    pd.DataFrame - dataframe of annotation data in DLC format
    '''
    is_ma = is_multianimal(dlc_config)
    col_idx = make_index_from_dlc_config(dlc_config)
    row_idx = []
    dlc_data = {idx_val: [] for idx_val in col_idx.values}


    keyfunc = lambda a: a['file_name']
    sorted_annot = sorted(intermediate_annotations, key=keyfunc)
    errors_found = 0
    for group, annots in itertools.groupby(sorted_annot, key=keyfunc):
        row_idx.append(tuple(group.replace(r'\\', '/').split('/')))
        # fill across the board with None
        for value in dlc_data.values():
            value.append(None)

        for annot in annots:
            if is_ma:
                if annot['individual'] is None:
                    # unique bodypart
                    key = (dlc_config['scorer'], 'single', annot['bodypart'])
                else:
                    # multi animal bodypart
                    key = (dlc_config['scorer'], annot['individual'], annot['bodypart'])
            else:
                key = (dlc_config['scorer'], annot['bodypart'])
            #print(annot['file_name'], key)
            try:
                dlc_data[(*key, 'x')][-1] = annot['x']
                dlc_data[(*key, 'y')][-1] = annot['y']
            except KeyError:
                errors_found += 1
                if annot['bodypart'] in dlc_config['multianimalbodyparts'] and annot['individual'] is None:
                    rationale = 'bodypart is a multianimal bodypart, but no relationship to an individual was found!'
                elif annot['bodypart'] in dlc_config['uniquebodyparts'] and annot['individual'] is not None:
                    rationale = 'bodypart is a unique bodypart and should not have a relationship with an individual, but one was found'
                else:
                    rationale = 'Unknown'

                message = 'ERROR! Data seems to violate the DLC annotation schema!\n' \
                         f' -> Task: {annot["task_id"]}\n' \
                         f' -> Image: "{annot["file_name"]}"\n' \
                         f' -> Bodypart: {annot["bodypart"]}\n'
                if is_ma:
                    message += f' -> Individual: {annot.get("individual", None)}\n'
                message += f' -> Rationale: {rationale}\n'
                print(message)

    dlc_df = pd.DataFrame(dlc_data, index=pd.MultiIndex.from_tuples(row_idx), columns=col_idx)

    return dlc_df, errors_found


def split_annotations_by_directory(intermediate_annotations: List[dict]) -> Dict[str, List[dict]]:
    ''' Split annotations into groups according to their file name

    Parameters:
    intermediate_annotations (List[dict]): "intermediate-style" annotations

    Returns:
    Dict[str, List[dict]] - grouped annotations with group as string keys and list of annotations as values
    '''
    grouped = {}

    for annot in intermediate_annotations:
        path, _ = os.path.split(annot['file_name'])
        _, group = os.path.split(path)
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(annot)

    return grouped
