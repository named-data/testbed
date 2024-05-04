from jinja2 import Environment, FileSystemLoader, StrictUndefined
from os import listdir
from os.path import isfile, join
import hashlib
import json
import pathlib
import subprocess
import sys
import yaml


init_values_path = './rendering_init_values.yml'


def get_templates(path):
    """
    Arguments:
    - path: path to the directory to get all files/templates from

    This function takes in the path to a directory, and returns all files
    in the directory as a list.
    """
    return [path + f for f in listdir(path) if isfile(join(path, f))]


def get_hash(template_path):
    """
    Arguments:
    - template_path: path to the template whose hash is desired

    This function takes in a path to a template, and returns the md5 hash of
    the contents of the file.
    """
    return hashlib.md5(open(template_path, 'rb').read()).hexdigest()


def container_running(container_status):
    """
    Arguments:
    - container_status: string output of the docker compose ps command

    This function takes in the string output of the docker compose ps command, and
    converts it to JSON to parse the state of the container. It returns whether or
    not the container is running.
    """
    try:
        to_json = json.loads(container_status)
    except json.decoder.JSONDecodeError:
        return False

    RUNNING = "running"
    if 'State' in to_json.keys():
        return to_json['State'] == RUNNING
    return False


def main():
    """
    Arguments:
    - node_name: any case is fine, it will be converted to upper

    This file will re-render all available templates with the provided values. If
    any values have changed (or the service has not been started before, indicated
    by no rendered templates), the service corresponding to the template with
    new values will be rebuilt and restarted. This file will also restart any
    service that is not running.
    """
    arguments = sys.argv
    if (len(arguments) < 2):
        raise Exception('No node provided.')

    # Get rendering init values as dict
    init_values = {}
    with open(init_values_path) as stream:
        try:
            init_values = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Load environment and templates for each service. Set undefined to StrictUndefined to throw
    # a noisy error if a value that is present in the template is not passed in as a value.
    environment = Environment(loader=FileSystemLoader(
        init_values['environment_path']), undefined=StrictUndefined)

    # Get the host_vars from the node name and place into dictionary
    values_path = init_values['host_vars_path'] + arguments[1].upper()
    render_values = {}
    with open(values_path) as stream:
        try:
            render_values = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Get all host vars, so we can access neighbors while filling in the templates.
    host_vars = {}
    all_host_vars = get_templates(init_values['host_vars_path'])
    for host_path in all_host_vars:
        with open(host_path) as stream:
            try:
                host_vars[host_path.rsplit(
                    '/', 1)[-1]] = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    render_values['hostvars'] = host_vars

    # For each service, render templates with the corresponding values
    services = init_values['services']
    for service_name, v in services.items():
        templates_list = get_templates(v['template_path'])
        # Create the output directory if it does not exist
        output_path = v['output_template_path']
        pathlib.Path(output_path).mkdir(
            parents=True, exist_ok=True)
        for i in templates_list:
            content = ''
            template = environment.get_template(i)
            try:
                content = template.render(**render_values)
            except Exception as e:
                raise Exception('Variable in template but not values')

            # Get the hash for the existing template if it exists, then write
            # the updated template
            file_path = output_path + i.rsplit('/', 1)[-1][:-3]
            hash = None
            if pathlib.Path(file_path).is_file():
                hash = get_hash(file_path)
            with open(file_path, 'w') as fh:
                fh.write(content)

            # Check if the docker container is already running
            running_command = ['docker', 'compose',
                               'ps', '--format', 'json', service_name]
            result = subprocess.run(running_command, stdout=subprocess.PIPE)
            container_alive = container_running(result.stdout)
            # Restart the container if the hash has changed, or if it is not running,
            # or if this is the first time a template has been rendered for it.
            if container_alive and hash is not None and get_hash(file_path) != hash:
                subprocess.call(
                    "docker compose restart " + service_name, shell=True)
            elif not container_alive or hash is None:
                subprocess.call(
                    "docker compose up -d " + service_name, shell=True)


if __name__ == '__main__':
    main()
