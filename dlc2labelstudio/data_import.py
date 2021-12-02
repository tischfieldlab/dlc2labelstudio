import datetime
import os
from typing import List, Optional

import tqdm
from label_studio_sdk.project import Project

from dlc2labelstudio.dlc_data import (collect_dataset, filter_dataset,
                                      load_dlc_annotations_for_image)
from dlc2labelstudio.ls_annot_parser import pick_filenames_from_tasks
from dlc2labelstudio.ls_client import (add_task_to_project, export_tasks,
                                       get_current_user_info, upload_data_file)


def import_dlc_data(project: Project, dlc_config: dict, update: bool=False, filter: Optional[List[str]]=None) -> List[dict]:
    ''' Import DLC project data into a label studio project

    Parameters:
    project (Project): a label studio project instance
    dlc_config (dict): DLC project configuration data
    update (bool): If true, only perform a differential update, otherwise import all found images
    filter (List[str]|None): If not None, filter discovered images by this criteria

    Returns:
    List[dict] - information about the imported files
    '''
    user = get_current_user_info(project)
    dataset_root = os.path.join(dlc_config['project_path'], 'labeled-data')
    files_to_upload = collect_dataset(dataset_root)
    print(f'Discovered {len(files_to_upload)} total images in the DLC Project')


    if filter is not None:
        files_to_upload = filter_dataset(files_to_upload, filter)
        print(f' -> Filtering is active, {len(files_to_upload)} images remaining which matched filters.')


    if update:
        tasks = export_tasks(project, export_type='JSON')
        existing = pick_filenames_from_tasks(tasks)
        discovered_short = [p.replace(dlc_config['project_path'] + os.path.sep, '') for p in files_to_upload]
        new_items = sorted(list(set(discovered_short) - set(existing)))
        new_items = [os.path.join(dlc_config['project_path'], n) for n in new_items]
        print(f' -> {len(new_items)} of these appear to be new images, not existing in the label studio project')
        print(f' -> You selected to update an existing project; only new images will be added to the label studio project')

        if len(new_items) <= 0:
            print('The project appears to be up to date!')
            return []
        else:
            print(f' -> Beginning upload...')
            files_to_upload = new_items

    else:
        if len(files_to_upload) <= 0:
            print('No images were found to upload!')
            return []
        else:
            print(f'Discovered {len(files_to_upload)} images in the DLC Project, beginning upload...')

    uploads = []
    for fup in tqdm.tqdm(files_to_upload, desc='uploading files'):
        annot = load_dlc_annotations_for_image(dlc_config, fup)
        _, up_deets = upload_data_file(project, fup)
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

        add_task_to_project(project, task)

    return uploads


def import_generic_ls_tasks(project: Project, tasks: List[dict]):
    ''' Import generic tasks in label studio format into an existing project

    Will upload any detected file paths that exist on the current machine from the task,
    and then import the task definition.

    Parameters:
    project (Project): a label studio project instance
    tasks (List[dict]): list of task definitions
    '''
    uploads = []
    for task in tqdm.tqdm(tasks, desc='Importing Tasks'):

        uploadable_files = get_files_from_task_data(task)
        for fup in tqdm.tqdm(uploadable_files, desc='Uploading Files', leave=False):
            _, up_deets = upload_data_file(project, fup)
            up_deets['original_file'] = fup
            uploads.append(up_deets)
            task['data'] = replace_dict_values(task['data'], fup, f"/data/{up_deets['file']}")

        add_task_to_project(project, task)

    return uploads


def get_files_from_task_data(task: dict):
    ''' Find files in task data

    Filters out duplicates and ensures files exist on the file system

    Parameters:
    task (dict): dict containing a task definition, assumed to have a `data` key

    Returns:
    List[str] - paths that look like files
    '''
    files = []
    for k, v in task['data'].items():
        if isinstance(v, str):
            files.append(v)
        elif isinstance(v, list):
            files.extend(v)
        else:
            raise ValueError(f'Warning: expected str or list[str] in task data, not {type(v)}!')

    files = list(set(files))
    files = list(filter(lambda f: os.path.exists(f), files))
    return files


def replace_dict_values(data: dict, search: str, replace: str) -> dict:
    for k, v in data.items():
        if isinstance(v, str) and v == search:
            data[k] = replace
        elif isinstance(v, list):
            for vi, val in enumerate(v):
                if val == search:
                    data[k][vi] = replace
        elif isinstance(v, dict):
            data[k] = replace_dict_values(v, search, replace)

    return data
