from jinja2 import Environment, FileSystemLoader, StrictUndefined
from os import listdir
from os.path import isfile, join
import docker
import hashlib
import pathlib
import subprocess
import sys
import yaml


init_values_path = './rendering_init_values.yml'


def get_templates(path):
    return [path + f for f in listdir(path) if isfile(join(path, f))]


def get_hash(template_path):
    return hashlib.md5(open(template_path, 'rb').read()).hexdigest()


def container_running(container_name):
    RUNNING = "running"

    docker_client = docker.from_env()

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound as exc:
        print(f"Container not running\n{exc.explanation}")
    else:
        container_state = container.attrs["State"]
        return container_state["Status"] == RUNNING


def main():
    """
    TODO: fix
    The arguments when calling render_templates.py are:
        - path_to_values_file: the path to the values file to be used
        - nfd (optional): if this is specified, the template for nfd will be rendered
        - nlsr (optional): if this is specified, the template for nlsr will be rendered
        - ndnping (optional): if this is specified, the template for ndnping will be rendered
    If only the values file is specified, all templates will be rendered. The order of arguments
    must place the values file first, before any services whose templates should be rendered.
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
                # print(e)
                raise Exception('Variable in template but not values')

            file_path = output_path + i.rsplit('/', 1)[-1][:-3]
            print(file_path)
            hash = None
            if pathlib.Path(file_path).is_file():
                hash = get_hash(file_path)
            with open(file_path, 'w') as fh:
                fh.write(content)
            if container_running(service_name) and hash is not None and get_hash(file_path) != hash:
                # restart the service
                subprocess.call("docker compose restart -d " + service_name, shell=True)
            else:
                # start the service, since no templates existed for it previously, or it was down
                subprocess.call("docker compose up -d "+ service_name, shell=True)


if __name__ == '__main__':
    main()
