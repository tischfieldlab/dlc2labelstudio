import datetime
import os
from typing import List

import tqdm
from label_studio_sdk.project import Project

from dlc2labelstudio.dlc_data import (collect_dataset,
                                      load_dlc_annotations_for_image)
from dlc2labelstudio.ls_client import (add_task_to_project,
                                       get_current_user_info, upload_data_file)


def import_data(project: Project, dlc_config: dict) -> List[dict]:
    ''' Import DLC project data into a label studio project

    Parameters:
    project (Project): a label studio project instance
    dlc_config (dict): DLC project configuration data

    Returns:
    List[dict] - information about the imported files
    '''
    user = get_current_user_info(project)
    dataset_root = os.path.join(dlc_config['project_path'], 'labeled-data')
    files_to_upload = collect_dataset(dataset_root)
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
