import datetime
import glob
import os
import shutil
import traceback
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import numpy.typing as npt
import pandas as pd
import ruamel.yaml as yaml
import seaborn as sns
import tqdm
from label_studio_sdk import Client
from label_studio_sdk.project import Project

from dlc2labelstudio.ls_annot_parser import read_annotations


def create_client(url: str, api_key: str) -> Client:
    ls = Client(url=url, api_key=api_key)
    ls.check_connection()
    return ls


def create_project(client: Client, dlc_config: dict) -> Project:
    project = client.start_project(
        title=dlc_config['Task'],
        label_config=create_label_config(dlc_config)
    )
    return project

def fetch_project(client: Client, project_id: int) -> Project:
    return client.get_project(project_id)


def import_data(project: Project, dlc_config: dict):
    user = get_current_user_info(project)
    dataset_root = os.path.join(dlc_config['project_path'], 'labeled-data')
    files_to_upload = collect_dataset(dataset_root)
    uploads = []
    for fup in tqdm.tqdm(files_to_upload, desc='uploading files'):
        annot = load_dlc_annotations_for_image(dlc_config, fup)
        response, up_deets = upload_data_file(project, fup)
        up_deets['original_file'] = fup.replace(dlc_config['project_path'] + os.path.sep, '')
        uploads.append(up_deets)

        task = {
            'data': {
                'image': f"/data/{up_deets['file']}"
            },
            'meta': {
                'original_file': up_deets['original_file']
            }
        }
        if annot is not None:
            task['annotations'] = [{
                **annot,
                "was_cancelled": False,
                "ground_truth": False,
                "created_at": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                "updated_at": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                "lead_time": 0,
                "result_count": 1,
                "completed_by": user['id']
            }]

        add_tasks_to_project(project, task)

    return uploads


def export_tasks(project: Project, export_type='JSON'):
    """ Export annotated tasks.

    Parameters
    ----------
    export_type: string
        Default export_type is JSON.
        Specify another format type as referenced in <a href="https://github.com/heartexlabs/label-studio-converter/blob/master/label_studio_converter/converter.py#L32">
        the Label Studio converter code</a>.

    Returns
    -------
    list of dicts
        Tasks with annotations

    """
    response = project.make_request(
        method='GET',
        url=f'/api/projects/{project.id}/export?exportType={export_type}'
    )
    return response.json()


def get_current_user_info(project: Project) -> dict:
    response = project.make_request(
        method='GET',
        url=f'/api/current-user/whoami',
    )
    return response.json()

def collect_dataset(base_dir: str) -> List[str]:
    search = os.path.join(base_dir, '**', '*.png')
    items = glob.glob(search, recursive=True)
    items = items[:10] # limit size for debug testing
    return items


def load_dlc_annotations_for_image(dlc_config: dict, image_path: str) -> Union[dict, None]:
    try:
        img_rel_path = image_path.replace(dlc_config['project_path'] + os.path.sep, '')
        annot_path = os.path.join(os.path.dirname(image_path), f'CollectedData_{dlc_config["scorer"]}.h5')
        if not os.path.exists(annot_path):
            return None

        annots = pd.read_hdf(annot_path)

        img = read_image(image_path)
        height, width = img.shape[:2]

        out = []
        for bp in annots.columns.levels[1].values:
            out.append({
                "original_width": width,
                "original_height": height,
                "image_rotation": 0,
                "value": {
                    "x": annots.loc[img_rel_path, (dlc_config["scorer"], bp, 'x')] / width * 100,
                    "y": annots.loc[img_rel_path, (dlc_config["scorer"], bp, 'y')] / height * 100,
                    "width": 0.2666,
                    "keypointlabels": [ bp ]
                },
                "from_name": "keypoint-label",
                "to_name": "image",
                "type": "keypointlabels"
            })

        return {
            'result': out
        }
    except:
        tqdm.tqdm.write(traceback.format_exc())
        None


def upload_data_file(project: Project, file: str):
    with open(file, mode='rb') as f:
        response = project.make_request(
            method='POST',
            url=f'/api/projects/{project.id}/import',
            files={'file': f},
            params={'commit_to_project': False}
        )
        jdata = response.json()
        deets = get_upload_details(project, jdata['file_upload_ids'][0])
        return jdata, deets


def get_upload_details(project: Project, upload_id: int):
    response = project.make_request(
        method='GET',
        url=f'/api/import/file-upload/{upload_id}',
    )
    return response.json()


def add_tasks_to_project(project: Project, tasks: dict):
    response = project.make_request(
        method='POST',
        url=f'/api/projects/{project.id}/import',
        json=tasks,
        params={'return_task_ids': True}
    )
    response.json()


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
    with open(yaml_file, 'r') as f:
        yml = yaml.YAML(typ='safe')
        return yml.load(f)


def write_yaml(yaml_file: str, data: dict) -> None:
    ''' Write a dict object into a yaml file

    Parameters:
    yaml_file (str): path to yaml file
    data (dict): dict of data to write to `yaml_file`
    '''
    with open(yaml_file, 'w') as f:
        yml = yaml.YAML(typ='safe')
        yml.default_flow_style = False
        yml.dump(data, f)



def create_label_config(dlc_config: dict, palette: str='bright') -> str:
    template = '<View style="display: flex;">\n' \
             + '    <View style="flex: 90%">\n' \
             + '        <Image name="image" value="$image" width="750px" maxWidth="1000px" zoom="true" zoomControl="true" brightnessControl="true" contrastControl="true" />\n' \
             + '    </View>\n' \
             + '    <View style="flex: 10%; margin-left: 1em">\n' \
             + '        <Header value="Keypoints" />\n' \
             + '        <KeyPointLabels name="keypoint-label" toName="image" strokewidth="2" opacity="1" >\n'

    colors = sns.color_palette(palette, len(dlc_config['bodyparts']))
    for bp, color in zip(dlc_config['bodyparts'], colors):

        template += (' ' * 4 * 3) + f'<Label value="{bp}" background="{rgb_to_hex(color)}"/>'

    template += '        </KeyPointLabels>\n' \
             +  '    </View>\n' \
             +  '</View>\n'

    return template

def float_rgb_to_int_rgb(color: Tuple[float, float, float]) -> Tuple[int, int, int]:
    return (int(c * 255) for c in color)

def clamp_rgb(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (int(max(0, min(c, 255))) for c in color)

def rgb_to_hex(color: Tuple[int, int, int]) -> str:
    r, g, b = clamp_rgb(float_rgb_to_int_rgb(color))
    return f'#{r:02x}{g:02x}{b:02x}'


def convert_ls_annot_to_dlc(ls_annotations: List[dict], dlc_config: dict, split=True):
    data = read_annotations(ls_annotations )#keypoint_names=dlc_config['bodyparts']

    if split:
        grouped = split_annotations_by_directory(data)
        for group, group_data in grouped.items():
            dlc_df = intermediate_annotations_to_dlc(group_data, dlc_config)
            save_dlc_annots(dlc_df, dlc_config, group)
    else:
        dlc_df = intermediate_annotations_to_dlc(data, dlc_config)
        save_dlc_annots(dlc_df, dlc_config)


def save_dlc_annots(annotations: pd.DataFrame, dlc_config: dict, group: Optional[str]=None):
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


def backup_existing_file(origional_path: str):

    counter = 0
    new_path = origional_path
    base, ext = os.path.splitext(origional_path)
    while os.path.exists(new_path):
        counter += 1
        new_path = f'{base}.backup-{counter}{ext}'

    shutil.copy2(origional_path, new_path)
    return new_path


def intermediate_annotations_to_dlc(intermediate_annotations: List[dict], dlc_config: dict):
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
            row_data.extend([
                kpts[bp]['x'],
                kpts[bp]['y'],
            ])
        dlc_data.append(row_data)
    dlc_df = pd.DataFrame(dlc_data, index=row_idx, columns=col_idx)

    return dlc_df


def split_annotations_by_directory(intermediate_annotations: List[dict]):
    grouped = {}

    for annot in intermediate_annotations:
        group = annot['file_name'].split(os.sep)[1]
        if group not in grouped:
            grouped[group] = []
        grouped[group].append(annot)

    return grouped
