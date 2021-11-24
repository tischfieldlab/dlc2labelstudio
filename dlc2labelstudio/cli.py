import matplotlib

matplotlib.use('Agg')

import os

import click

from dlc2labelstudio.data_export import convert_ls_annot_to_dlc
from dlc2labelstudio.data_import import import_data
from dlc2labelstudio.io import read_yaml, write_yaml
from dlc2labelstudio.label_config import create_label_config
from dlc2labelstudio.ls_client import (create_client, create_project,
                                       export_tasks, fetch_project)

orig_init = click.core.Option.__init__
def new_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.show_default = True
# end new_init()
click.core.Option.__init__ = new_init


@click.group()
def cli():
    pass


@cli.command(name='import-dlc-project', help="Import DLC data into Label Studio")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
@click.option('--update-project', default=None, type=int, help='Perform a differential update between DLC and a label studio project.')
@click.option('--filter', default=None, multiple=True, help='Limit importing of images with filename matching a pattern')
@click.option('--endpoint', default='http://labelstudio.hginj.rutgers.edu/', help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def import_dlc_project(dlc_project_dir, update_project, filter, endpoint, key):
    print()

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))

    client = create_client(url=endpoint, api_key=key)

    if update_project is None:
        label_config = create_label_config(dlc_config)
        project = create_project(client, dlc_config, label_config)
    else:
        project = fetch_project(client, update_project)
        print(f'Found label studio project "{project.title}" (id={project.id})\n')

    if len(filter) <= 0:
        filter = None

    uploaded_files = import_data(project, dlc_config, update=(update_project is not None), filter=filter)

    upload_manifest = os.path.join(dlc_config['project_path'], f'label-studio-tasks-project-{project.id}.yaml')
    if update_project is not None:
        prev_uploaded_files = read_yaml(upload_manifest)
        uploaded_files = prev_uploaded_files + uploaded_files
    write_yaml(upload_manifest, uploaded_files)


@cli.command(name='export-ls-project', help="Export annotations from Label Studio into DLC format")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
@click.argument('ls-project-id', type=int)
@click.option('--endpoint', default='http://labelstudio.hginj.rutgers.edu/', help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def export_ls_project(dlc_project_dir, ls_project_id, endpoint, key):
    print()

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))
    client = create_client(url=endpoint, api_key=key)
    project = fetch_project(client, ls_project_id)
    tasks = export_tasks(project, export_type='JSON')
    print(f'Found {len(tasks)} in label studio project "{project.title}" (id={project.id})')
    convert_ls_annot_to_dlc(tasks, dlc_config)


if __name__ == '__main__':
    cli()
