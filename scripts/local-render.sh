#!/bin/bash

# Render configurations for local 3-node testbed
# Usage: ./scripts/local-render.sh

set -e

cd "$(dirname "${BASH_SOURCE[0]}")"/..

echo "Rendering configurations for LOCAL1, LOCAL2, LOCAL3..."

# Create dist directories
mkdir -p dist-local1/{nfd,ndnpingserver,nlsr/state}
mkdir -p dist-local2/{nfd,ndnpingserver,nlsr/state}
mkdir -p dist-local3/{nfd,ndnpingserver,nlsr/state}

# We need to run the framework with modified render paths
# Use a Python script to render with correct paths

python3 - << 'EOF'
import os
import sys
import pathlib
import yaml
import jinja2

# Add framework to path
sys.path.insert(0, 'framework')
from internal import utils

CONFIG_FILE = 'config.yml'

JINJA_FUNCTIONS = {
    'path_exists': lambda path: os.path.exists(path),
    'read_file': lambda path: open(path).read(),
    'oneline': lambda text: ''.join(text.splitlines()),
    'list': lambda obj: list(obj),
    'str': lambda obj: str(obj),
}

# Load main config
with open(CONFIG_FILE) as f:
    config = yaml.safe_load(f)

# Services to render for local testing
local_services = ['nfd', 'ndnpingserver', 'nlsr']

# Load all host vars
all_host_vars = {}
for host_path in utils.get_files(config['host_vars_path']):
    with open(host_path) as f:
        host_name = os.path.basename(host_path)
        all_host_vars[host_name] = yaml.safe_load(f)
        all_host_vars[host_name]['inventory_hostname'] = host_name
        all_host_vars[host_name].update(config['globals'])

# Setup Jinja environment
environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(config['environment_path']),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True)

# Render for each local node
for node_num, node_name in enumerate(['LOCAL1', 'LOCAL2', 'LOCAL3'], 1):
    print(f"Rendering {node_name}...")
    
    render_vars = all_host_vars[node_name].copy()
    render_vars['hostvars'] = all_host_vars
    
    dist_dir = f"dist-local{node_num}"
    
    for service in local_services:
        service_config = config['services'].get(service, {})
        template_path = service_config.get('template_path')
        
        if not template_path:
            continue
            
        render_path = f"{dist_dir}/{service}"
        pathlib.Path(render_path).mkdir(parents=True, exist_ok=True)
        
        # Get all templates
        template_paths = utils.get_files(template_path, recursive=True)
        
        for tpl_path in template_paths:
            output_basename = os.path.basename(tpl_path)
            
            # Skip the production nlsr.conf.j2 and use local version instead
            if service == 'nlsr' and 'nlsr.conf.j2' in tpl_path and 'local' not in tpl_path:
                continue
            
            # Use local template for nlsr config
            if service == 'nlsr' and 'nlsr.local.conf.j2' in tpl_path:
                output_basename = 'nlsr.conf'
                output_content = environment.get_template(tpl_path).render(**render_vars, **JINJA_FUNCTIONS)
            elif tpl_path.endswith('.j2'):
                output_basename = os.path.splitext(output_basename)[0]
                output_content = environment.get_template(tpl_path).render(**render_vars, **JINJA_FUNCTIONS)
            else:
                with open(tpl_path, 'r') as f:
                    output_content = f.read()
            
            # Get relative path
            relative_path = os.path.dirname(os.path.relpath(tpl_path, template_path))
            output_dir = os.path.join(render_path, relative_path)
            output_path = os.path.join(output_dir, output_basename)
            
            os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(output_content)
            
            print(f"  -> {output_path}")

print("\nDone! Configurations rendered to dist-local1/, dist-local2/, dist-local3/")
EOF

echo ""
echo "To start the local testbed:"
echo "  docker compose -f docker-compose.local.yml up -d"
echo ""
echo "To check status:"
echo "  docker exec testbed-local-nfd1-1 nfdc status report"
echo "  docker exec testbed-local-nfd2-1 nfdc status report"
echo "  docker exec testbed-local-nfd3-1 nfdc status report"
echo ""
echo "To test connectivity:"
echo "  docker exec testbed-local-nfd1-1 ndnping /ndn/local/node2"
