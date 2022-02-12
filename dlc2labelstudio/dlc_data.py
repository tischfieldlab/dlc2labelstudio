import fnmatch
import glob
import math
import os
import traceback
from typing import List, Union

import pandas as pd
import tqdm

from dlc2labelstudio.io import read_image

def is_multianimal(dlc_config: dict) -> bool:
    return 'multianimalproject' in dlc_config and dlc_config['multianimalproject']

def collect_dataset(base_dir: str) -> List[str]:
    ''' Find images in a DLC dataset

    Parameters:
    base_dir (str): base directory to search within

    Returns:
    List[str] - list of discovered file paths
    '''
    search = os.path.join(base_dir, '**', '*.png')
    items = glob.glob(search, recursive=True)
    #items = items[:10] # limit size for debug testing
    return items


def filter_dataset(dataset: List[str], filters: List[str]) -> List[str]:
    ''' Filter a list of filenames matching filters

    A filename only needs to match at least one filter to be included in the output

    Parameters:
    dataset (List[str]): List of filenames to filter
    filters (List[str]): List of filters to apply

    Returns:
    List[str]: List of filenames matching at least one filter
    '''
    out = []
    for item in dataset:
        for filter in filters:
            if fnmatch.fnmatch(item, filter):
                out.append(item)
                break
    return out


def load_dlc_annotations_for_image(dlc_config: dict, image_path: str) -> Union[dict, None]:
    ''' Load existing DLC annotations for a given image. If no annotations could be found, None is returned

    Parameters:
    dlc_config (dict): DLC project configuration data
    image_path (str): path to an image file

    Returns:
    If annotation data can be found, a dictionary of annotation data is returned, otherwise None
    '''
    is_ma = is_multianimal(dlc_config)
    try:
        img_rel_path = image_path.replace(dlc_config['project_path'] + os.path.sep, '')
        annot_path = os.path.join(os.path.dirname(image_path), f'CollectedData_{dlc_config["scorer"]}.h5')
        if not os.path.exists(annot_path):
            return None

        annots = pd.read_hdf(annot_path)

        if is_ma:
            to_iter = zip(annots.columns.levels[1].values, annots.columns.levels[2].values)
        else:
            to_iter = (annots.columns.levels[1].values,)

        img = read_image(image_path)
        height, width = img.shape[:2]

        out = []
        indv_map = {}
        if is_ma:
            # if multi animal, need to append a indv
            for indv in list(set(annots.columns.levels[1].values)):
                indv_id = 'my_id'
                indv_map[indv] = indv_id
                out.append({
                    "original_width": width,
                    "original_height": height,
                    "image_rotation": 0,
                    "value": {
                        "x": 0,
                        "y": 0,
                        "width": width,
                        "height": height,
                        "rotation": 0,
                        "rectanglelabels": [ indv ]
                    },
                    "id": indv_id,
                    "from_name": "individuals",
                    "to_name": "image",
                    "type": "rectanglelabels"
                })

        for idx in to_iter:
            x_pos = annots.loc[img_rel_path, (dlc_config["scorer"], *idx, 'x')]
            y_pos = annots.loc[img_rel_path, (dlc_config["scorer"], *idx, 'y')]
            if math.isnan(x_pos) or math.isnan(y_pos):
                continue
            kpt_id = 'my_kpt_id'

            out.append({
                "original_width": width,
                "original_height": height,
                "image_rotation": 0,
                "value": {
                    "x": x_pos / width * 100,
                    "y": y_pos / height * 100,
                    "width": 0.2666,
                    "keypointlabels": [ idx[-1] ]
                },
                "from_name": "keypoint-label",
                "to_name": "image",
                "type": "keypointlabels",
                "id": kpt_id
            })

            if is_ma:
                # need to add relations
                out.append({
                    "from_id":  kpt_id,
                    "to_id": indv_map[idx[0]],
                    "type": "relation",
                    "direction": "right"
                })

        return {
            'result': out
        }
    except:
        tqdm.tqdm.write(traceback.format_exc())
        None
