import os

import click
import tqdm
from click_option_group import RequiredMutuallyExclusiveOptionGroup, optgroup

from dlc2labelstudio.data_export import convert_ls_annot_to_dlc
from dlc2labelstudio.data_import import (import_dlc_data,
                                         import_generic_ls_tasks)
from dlc2labelstudio.io import (click_monkey_patch_option_show_defaults,
                                read_label_config, read_ls_tasks, read_yaml,
                                write_ls_tasks, write_yaml)
from dlc2labelstudio.label_config import create_label_config
from dlc2labelstudio.ls_client import (create_client, create_project,
                                       create_project_from_dlc, export_tasks,
                                       fetch_project)

click_monkey_patch_option_show_defaults()


@click.group()
def cli():
    ''' Toolbox for importing DLC data into label-studio and annotated data
        from label-studio back into DLC.
    '''
    pass # pylint: disable=unnecessary-pass


DEFAULT_LS_HOST = 'http://labelstudio.hginj.rutgers.edu/'

@cli.command(name='import-dlc-project', short_help="Import DLC data into Label Studio")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
@click.option('--update-project', default=None, type=int, help='Perform a differential update between DLC and a label studio project.')
@click.option('--filter', 'filter_patterns', default=None, multiple=True, help='Limit importing of images with filename matching a pattern')
@click.option('--endpoint', default=DEFAULT_LS_HOST, help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def import_dlc_project(dlc_project_dir, update_project, filter_patterns, endpoint, key):
    ''' Import DLC data into Label Studio
    '''
    print()

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))

    client = create_client(url=endpoint, api_key=key)

    if update_project is None:
        project = create_project_from_dlc(client, dlc_config)
    else:
        project = fetch_project(client, update_project)
        print(f'Found label studio project "{project.title}" (id={project.id})\n')

    if len(filter_patterns) <= 0:
        filter_patterns = None

    uploaded_files = import_dlc_data(project, dlc_config, update=(update_project is not None), filter_patterns=filter_patterns)

    upload_manifest = os.path.join(dlc_config['project_path'], f'label-studio-tasks-project-{project.id}.yaml')
    if update_project is not None:
        prev_uploaded_files = read_yaml(upload_manifest)
        uploaded_files = prev_uploaded_files + uploaded_files
    write_yaml(upload_manifest, uploaded_files)


@cli.command(name='export-ls-project', short_help="Export annotations from Label Studio into DLC format")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
@click.argument('ls-project-id', type=int)
@click.option('--endpoint', default=DEFAULT_LS_HOST, help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def export_ls_project(dlc_project_dir, ls_project_id, endpoint, key):
    ''' Export annotations from Label Studio into DLC format
    '''
    print()

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))
    client = create_client(url=endpoint, api_key=key)
    project = fetch_project(client, ls_project_id)
    tasks = export_tasks(project, export_type='JSON')
    print(f'Found {len(tasks)} tasks in label studio project "{project.title}" (id={project.id})')
    convert_ls_annot_to_dlc(tasks, dlc_config)


@cli.command(name='merge-ls-annotations', short_help="Merge multiple label studio json files into a single file")
@click.argument('ls_annotation_file', nargs=-1, type=click.Path(exists=True, dir_okay=False))
@click.argument('output', type=click.Path())
def merge_ls_annotations(ls_annotation_file, output):
    ''' Merge multiple label studio json files into a single file
    '''
    merged = []
    for ls_file in tqdm.tqdm(ls_annotation_file, desc='Annotation files', leave=False):
        tasks = read_ls_tasks(ls_file)
        tqdm.tqdm.write(f'{len(tasks)} tasks found in "{ls_file}"')
        merged.extend(tasks)

    write_ls_tasks(output, merged)


@cli.command(name='import-ls-tasks', short_help="Import (generic) tasks into label studio")
@click.argument('tasks', nargs=-1, type=click.Path(dir_okay=False))
@optgroup.group('Project Configuration', cls=RequiredMutuallyExclusiveOptionGroup, help='The sources of the input data')
@optgroup.option('--update-project', default=None, type=int, help='Project ID of an existing label studio project to import tasks into.')
@optgroup.option('--new-project', default=None, type=str, help='Create a new task with this title for importing tasks into.')
@click.option('--label-config', type=click.Path(exists=True, dir_okay=False),
              help='Path to a file containing a labeling configuration. Required if using --new-project.')
@click.option('--endpoint', default=DEFAULT_LS_HOST, help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def import_ls_tasks(tasks, update_project, new_project, label_config, endpoint, key):
    ''' Import (generic) tasks into label studio
    '''

    client = create_client(url=endpoint, api_key=key)

    if update_project is None:
        label_config = read_label_config(label_config)
        project = create_project(client, new_project, label_config)
    else:
        project = fetch_project(client, update_project)
        print(f'Found label studio project "{project.title}" (id={project.id})\n')

    all_tasks = []
    for task_file in tqdm.tqdm(tasks, desc='Reading Task Files', leave=False):
        all_tasks.extend(read_ls_tasks(task_file))

    uploaded_files = import_generic_ls_tasks(project, all_tasks)

    upload_manifest = f'label-studio-tasks-project-{project.id}.yaml'
    if update_project is not None:
        prev_uploaded_files = read_yaml(upload_manifest)
        uploaded_files = prev_uploaded_files + uploaded_files
    write_yaml(upload_manifest, uploaded_files)


@cli.command(name='create-label-config', short_help="Create a label configuration based on a DLC project")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
def create_label_config_cli(dlc_project_dir):
    ''' Create a label configuration based on a DLC project
    '''
    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))
    label_config = create_label_config(dlc_config)
    print(label_config)


if __name__ == '__main__':
    cli()
