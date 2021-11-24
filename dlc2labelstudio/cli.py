import os

import click
from label_studio_sdk import project

from dlc2labelstudio.client import convert_ls_annot_to_dlc, create_client, create_project, export_tasks, fetch_project, import_data, read_yaml, write_yaml

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
@click.option('--endpoint', default='http://labelstudio.hginj.rutgers.edu/', help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def import_dlc_project(dlc_project_dir, endpoint, key):

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))

    client = create_client(url=endpoint, api_key=key)
    project = create_project(client, dlc_config)
    uploaded_files = import_data(project, dlc_config)

    upload_manifest = os.path.join(dlc_config['project_path'], 'label-studio-tasks.yaml')
    write_yaml(upload_manifest, uploaded_files)


@cli.command(name='export-ls-project', help="Export annotations from Label Studio into DLC format")
@click.argument('dlc-project-dir', type=click.Path(exists=True, file_okay=False))
@click.argument('ls-project-id', type=int)
@click.option('--endpoint', default='http://labelstudio.hginj.rutgers.edu/', help='URL to Label Studio instance')
@click.option('--key', required=True, help='Your personal API key')
def export_ls_project(dlc_project_dir, ls_project_id, endpoint, key):

    dlc_config = read_yaml(os.path.join(dlc_project_dir, 'config.yaml'))
    client = create_client(url=endpoint, api_key=key)
    project = fetch_project(client, ls_project_id)
    tasks = export_tasks(project, export_type='JSON')
    convert_ls_annot_to_dlc(tasks, dlc_config)





if __name__ == '__main__':
    cli()