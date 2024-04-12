from jinja2 import Environment, FileSystemLoader, StrictUndefined
from os import listdir
from os.path import isfile, join
import pathlib
import yaml

# Directory containing templates and value file
environment_path = "."
# Path for templates for NFD, NLSR, ndnping
nfd_template_path = "./nfd/templates/"
nlsr_template_path = "./nlsr/templates/"
ndnping_template_path = "./ndnping/templates/"
# Value file path
values_path = "./values/test_values"
# Load environment and templates for each service. Set undefined to StrictUndefined to throw
# a noisy error if a value that is present in the template is not passed in as a value.
environment = Environment(loader=FileSystemLoader(
    environment_path), undefined=StrictUndefined)
nfd_templates = [nfd_template_path +
                 f for f in listdir(nfd_template_path) if isfile(join(nfd_template_path, f))]
nlsr_templates = [nlsr_template_path + f for f in listdir(
    nlsr_template_path) if isfile(join(nlsr_template_path, f))]
ndnping_templates = [ndnping_template_path + f for f in listdir(
    ndnping_template_path) if isfile(join(ndnping_template_path, f))]
# Map the desired output directory to the corresponding templates
templates = {"./nfd/rendered_templates": nfd_templates,
             "./nlsr/rendered_templates": nlsr_templates,
             "./ndnping/rendered_templates": ndnping_templates}
render_values = {}

# Get values as dict
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
        template = environment.get_template(i)
        content = template.render(**render_values)

        file_name = i.rsplit('/', 1)[-1]
        with open(output_path + '/' + file_name, "w") as fh:
            fh.write(content)
