from jinja2 import Environment, FileSystemLoader, StrictUndefined
from os import listdir
from os.path import isfile, join
import pathlib
import sys
import yaml

# Directory containing templates and value file
environment_path = '.'

# Path for templates for NFD, NLSR, ndnping
nfd_template_path = './nfd/templates/'
nlsr_template_path = './nlsr/templates/'
ndnping_template_path = './ndnping/templates/'

# Path for output templates for NFD, NLSR, ndnping
nfd_output_template_path = './nfd/rendered_templates/'
nlsr_output_template_path = './nlsr/rendered_templates/'
ndnping_output_template_path = './ndnping/rendered_templates/'

# Load environment and templates for each service. Set undefined to StrictUndefined to throw
# a noisy error if a value that is present in the template is not passed in as a value.
environment = Environment(loader=FileSystemLoader(
    environment_path), undefined=StrictUndefined)


def get_templates(path):
    return [path + f for f in listdir(path) if isfile(join(path, f))]


def main():
    """
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
        raise Exception('No values file provided.')
    if (len(arguments) == 2):
        render_all = True

    values_path = arguments[1]
    render_all = False
    templates = {}
    if ('nfd' in arguments or render_all):
        templates[nfd_output_template_path] = get_templates(
            nfd_template_path)
    if ('nlsr' in arguments or render_all):
        templates[nlsr_output_template_path] = get_templates(
            nlsr_template_path)
    if ('ndnping' in arguments or render_all):
        templates[ndnping_output_template_path] = get_templates(
            ndnping_template_path)

    # Get values as dict
    render_values = {}
    with open(values_path) as stream:
        try:
            render_values = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Render every template in the directory with the corresponding values
    for output_path, template_list in templates.items():
        # Create the output directory if it does not exist
        pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)
        for i in template_list:
            content = ''
            template = environment.get_template(i)
            try:
                content = template.render(**render_values)
            except:
                raise Exception('Variable in template but not values')

            file_name = i.rsplit('/', 1)[-1]
            with open(output_path + file_name, 'w') as fh:
                fh.write(content)


if __name__ == '__main__':
    main()
