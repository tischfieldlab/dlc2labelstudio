from typing import List, Tuple

from label_studio_sdk import Client
from label_studio_sdk.project import Project

from dlc2labelstudio.label_config import create_label_config


def create_client(url: str, api_key: str) -> Client:
    ''' Create a label studio client

    Parameters:
    url (str): url of the label studio instance
    api_key (str): an access token generate by label studio

    Returns:
    Client - a label studio SDK client
    '''
    ls_client = Client(url=url, api_key=api_key)
    ls_client.check_connection()
    return ls_client


def create_project_from_dlc(client: Client, dlc_config: dict) -> Project:
    ''' Create a new project within Label Studio based on a label studio configuration

    The project will be named based on the `Task` key from `dlc_config`.
    A label_config will also be added to the project.

    Parameters:
    client (Client): label studio client object
    title (str): title of the project

    Returns:
    Project - the newly created project1
    '''
    label_config = create_label_config(dlc_config)
    return create_project(client, title=dlc_config['Task'], label_config=label_config)


def create_project(client: Client, title: str, label_config: str) -> Project:
    ''' Create a new project within Label Studio

    The project will be named using `title` and a labeling configuration
    will be added from `label_config`.

    Parameters:
    client (Client): label studio client object
    title (str): title of the project
    label_config (str): a labeling configuration to add to the project

    Returns:
    Project - the newly created project1
    '''
    print(f"Creating LS project named \"{title}\"")
    project = client.start_project(
        title=title,
        label_config=label_config
    )
    print(f" -> {project.get_url(f'/projects/{project.id}')}\n")
    return project


def fetch_project(client: Client, project_id: int) -> Project:
    ''' Find and return an existing label studio project

    Parameters:
    client (Client): label studio client object
    project_id (int): id of the project to fetch

    Returns:
    Project - project with id `project_id`
    '''
    return client.get_project(project_id)


def export_tasks(project: Project, export_type='JSON') -> List[dict]:
    ''' Export annotated tasks.

    https://labelstud.io/api#operation/api_projects_export_read

    Parameters:
    export_type (string): format of the task export.
    Default export_type is JSON.
    Specify another format type as referenced in
    <a href="https://github.com/heartexlabs/label-studio-converter/blob/master/label_studio_converter/converter.py#L32">
    the Label Studio converter code</a>.

    Returns
    list of dicts - Tasks with annotations
    '''
    response = project.make_request(
        method='GET',
        url=f'/api/projects/{project.id}/export?exportType={export_type}'
    )
    return response.json()


def get_current_user_info(client: Client) -> dict:
    ''' Return information about the current user

    https://labelstud.io/api#operation/api_current-user_whoami_read

    Parameters:
    client (Client): label studio client instance

    Returns:
    dict - containing current user information
    '''
    response = client.make_request(
        method='GET',
        url=f'/api/current-user/whoami',
    )
    return response.json()


def upload_data_file(project: Project, file: str) -> Tuple[dict, dict]:
    ''' Upload a data file to a label studio project

    https://labelstud.io/api#operation/api_projects_file-uploads_delete

    Parameters:
    project (Project): a label studio project instance
    file (str): path to the file to be uploaded

    Returns:
    Tuple[dict, dict] - tuple of (upload_response, upload_info)
    '''
    with open(file, mode='rb') as upload_file:
        response = project.make_request(
            method='POST',
            url=f'/api/projects/{project.id}/import',
            files={'file': upload_file},
            params={'commit_to_project': False}
        )
        jdata = response.json()
        deets = get_upload_details(project, jdata['file_upload_ids'][0])
        return jdata, deets


def get_upload_details(project: Project, upload_id: int) -> dict:
    ''' Return information about file uploaded to label studio

    https://labelstud.io/api#operation/api_import_file-upload_read

    Parameters:
    project (Project): a label studio project instance
    upload_id (int): upload id to return information for

    Returns:
    dict - containing data about the inquired upload
    '''
    response = project.make_request(
        method='GET',
        url=f'/api/import/file-upload/{upload_id}',
    )
    return response.json()


def add_task_to_project(project: Project, task: dict) -> dict:
    ''' Add a task to a project

    https://labelstud.io/api#operation/api_projects_import_create

    Parameters:
    project (Project): a label studio project instance
    task (dict): a label studio task

    Returns:
    dict - information about the operation
    '''
    response = project.make_request(
        method='POST',
        url=f'/api/projects/{project.id}/import',
        json=task,
        params={'return_task_ids': True}
    )
    return response.json()
