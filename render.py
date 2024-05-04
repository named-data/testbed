import os
import pathlib
import subprocess
import sys
import yaml
import jinja2

import compose
import utils

from dataclasses import dataclass

CONFIG_FILE = './config.yml'

@dataclass
class Config:
    environment_path: str
    host_vars_path: str
    services: dict[str, dict]

def render(node_name: str) -> None:
    """
    Arguments:
    - node_name: name of node (case sensitive)

    This file will re-render all available templates with the provided values. If
    any values have changed (or the service has not been started before, indicated
    by no rendered templates), the service corresponding to the template with
    new values will be rebuilt and restarted. This file will also restart any
    service that is not running.
    """

    # Read config file
    config = None
    with open(CONFIG_FILE) as stream:
        config = Config(**yaml.safe_load(stream))

    # Load environment and templates for each service. Set undefined to StrictUndefined to throw
    # a noisy error if a value that is present in the template is not passed in as a value.
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.environment_path),
        undefined=jinja2.StrictUndefined)

    # Get the host_vars from the node name and place into dictionary
    render_vars = {}
    with open(os.path.join(config.host_vars_path, node_name)) as stream:
        render_vars = yaml.safe_load(stream)

    # Get all host vars, so we can access neighbors while filling in the templates.
    all_host_vars = {}
    for host_path in utils.get_files(config.host_vars_path):
        with open(host_path) as stream:
            try:
                host_name = os.path.basename(host_path)
                all_host_vars[host_name] = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print("Error reading host vars file: ", host_path, exc)
    render_vars['hostvars'] = all_host_vars

    # For each service, render templates with the corresponding values
    for service, values in config.services.items():
        # Check if any file did change
        service_changed = False

        # Create the output directory if it does not exist
        render_path = values['render_path']
        pathlib.Path(render_path).mkdir(parents=True, exist_ok=True)

        # Get all templates for the service
        template_paths = utils.get_files(values['template_path'])

        # Render all templates for the service
        for template_path in template_paths:
            if not template_path.endswith('.j2'):
                continue

            # Load the template
            template = environment.get_template(template_path)

            # Render the template with the values
            content = template.render(**render_vars)

            # Get the output filename (remove .j2 extension)
            output_basename = os.path.splitext(os.path.basename(template_path))[0]
            output_path = os.path.join(render_path, output_basename)

            # Read the existing file if it exists
            existing_content = None
            if pathlib.Path(output_path).is_file():
                with open(output_path, 'r') as f:
                    existing_content = f.read()

            # Check if the content has changed
            if existing_content != content:
                print(f"Template {template_path} has changed.")
                service_changed = True
                with open(output_path, 'w') as f:
                    f.write(content)

        if service_changed and False:
            # Check if the docker container is already running
            service_status = compose.status(service)
            container_alive = compose.is_running(service_status)

            # Restart the container if the hash has changed, or if it is not running,
            # or if this is the first time a template has been rendered for it.
            if container_alive and hash is not None and utils.hash_file(file_path) != hash:
                subprocess.call(
                    "docker compose restart " + service, shell=True)
            elif not container_alive or hash is None:
                subprocess.call(
                    "docker compose up -d " + service_name, shell=True)


if __name__ == '__main__':
    arguments = sys.argv
    if (len(arguments) < 2):
        raise Exception('No node provided.')
    render(arguments[1])
