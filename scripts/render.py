import os
import pathlib
import subprocess
import yaml
import jinja2

from dataclasses import dataclass
from typing import Any

from . import conf
from . import compose
from . import utils

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
    config = conf.get()

    # Load environment and templates for each service. Set undefined to StrictUndefined to throw
    # a noisy error if a value that is present in the template is not passed in as a value.
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.environment_path),
        undefined=jinja2.StrictUndefined)

    # Get all host vars, so we can access neighbors while filling in the templates.
    all_host_vars: dict[str, dict] = {}
    for host_path in utils.get_files(config.host_vars_path):
        with open(host_path) as stream:
            try:
                host_name = os.path.basename(host_path)
                all_host_vars[host_name] = yaml.safe_load(stream)

                # Copy globals from config file
                all_host_vars[host_name]['inventory_hostname'] = host_name
                all_host_vars[host_name].update(config.globals)
            except yaml.YAMLError as exc:
                print("Error reading host vars file: ", host_path, exc)

    # Rendering variables for this node
    render_vars = all_host_vars[node_name].copy()
    render_vars['hostvars'] = all_host_vars

    # For each service, render templates with the corresponding values
    for service, values in config.services.items():
        # Check if any file did change
        service_changed = False

        # Create the output directory if it does not exist
        render_path = values.get('render_path')
        pathlib.Path(render_path).mkdir(parents=True, exist_ok=True)

        # Get all templates for the service
        base_template_path = values.get('template_path')
        template_paths = utils.get_files(base_template_path, recursive=True)

        # Render all templates for the service
        for template_path in template_paths:
            output_basename = os.path.basename(template_path)
            output_content = None

            # Render if this is a Jinja2 template
            if template_path.endswith('.j2'):
                # Remove the .j2 extension from the output filename
                output_basename = os.path.splitext(output_basename)[0]

                # Render the template with the values
                output_content = environment.get_template(template_path).render(**render_vars)
            else:
                # Read the file
                with open(template_path, 'r') as f:
                    output_content = f.read()

            # Get relative path of template to base directory
            relative_path = os.path.dirname(os.path.relpath(template_path, base_template_path))

            # Get the output filename (remove .j2 extension)
            output_dir = os.path.join(render_path, relative_path)
            output_path = os.path.join(output_dir, output_basename)

            # Create the output directory if it does not exist
            os.makedirs(output_dir, exist_ok=True)

            # Read the existing file if it exists
            existing_content = None
            if pathlib.Path(output_path).is_file():
                with open(output_path, 'r') as f:
                    existing_content = f.read()

            # Check if the content has changed
            if existing_content != output_content:
                print(f"File {output_path} has changed.")
                service_changed = True
                with open(output_path, 'w') as f:
                    f.write(output_content)

        # Check if the docker container is already running
        service_status = compose.status(service)
        service_running = compose.is_running(service_status)

        if not service_running:
            print(f"WARN: Service {service} is not running.")
            compose.up(service)
        elif service_changed:
            print(f"Service {service} has changed. Restarting.")
            compose.restart(service)

        # Run init script if status change
        if not service_running or service_changed:
            if init_exec := values.get('init_exec'):
                compose.exec(service, init_exec)
