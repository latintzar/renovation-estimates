#!/usr/bin/env python3
"""Build or run the original renovation app with cached local reports."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = SOURCE_ROOT/'frontend' if (SOURCE_ROOT/'frontend/package.json').is_file() else SOURCE_ROOT


def environment(base_path, state_dir):
    # A sample command never inherits provider credentials or cloud home profiles.
    keep = {'PATH', 'HOME', 'LANG', 'LC_ALL', 'TERM', 'TMPDIR', 'SYSTEMROOT', 'COMSPEC'}
    env = {name: value for name, value in os.environ.items() if name in keep}
    env.update(SAMPLE_MODE='1', NEXT_PUBLIC_SAMPLE_MODE='1', NEXT_PUBLIC_BASE_PATH=base_path,
               SAMPLE_DATA_DIR=str(state_dir), NEXT_TELEMETRY_DISABLED='1',
               AWS_EC2_METADATA_DISABLED='true', AWS_CONFIG_FILE=os.devnull,
               AWS_SHARED_CREDENTIALS_FILE=os.devnull, GCE_METADATA_HOST='127.0.0.1:9',
               GOOGLE_APPLICATION_CREDENTIALS='/recipient-google-credentials-not-configured')
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['dev', 'build', 'start'])
    parser.add_argument('--base-path', default='')
    parser.add_argument('--state-dir', type=Path, default=Path.home()/'.local/state/renovation-estimates-sample')
    parser.add_argument('--hostname', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3002)
    args = parser.parse_args()
    if args.base_path and not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)+', args.base_path):
        parser.error('Use an empty base path or path segments such as /apps/estimates.')
    if not 1024 <= args.port <= 65535:
        parser.error('Choose a port between 1024 and 65535.')
    if any(path.name != '.env.example' for path in ROOT.glob('.env*')):
        parser.error('Use a clean source checkout for sample mode; keep recipient configuration outside it.')
    state_dir = args.state_dir.expanduser().absolute()
    if state_dir.is_relative_to(ROOT):
        parser.error('Choose a state directory outside the checkout.')
    node = shutil.which('node')
    if not node:
        parser.error('Install Node 22.18+ in the Node 22 line.')
    env = environment(args.base_path, state_dir)
    version = subprocess.check_output([node, '--version'], text=True, env=env).strip()
    major, minor = map(int, version.lstrip('v').split('.')[:2])
    if major != 22 or minor < 18:
        parser.error('Use the tested Node 22.18+ runtime in the Node 22 line.')
    if args.action == 'start':
        if (ROOT/'server.js').is_file() and (ROOT/'sample-runtime.json').is_file():
            standalone = ROOT
            metadata = json.loads((ROOT/'sample-runtime.json').read_text())
            if metadata.get('basePath', '') != args.base_path or metadata.get('mode') != 'sample':
                parser.error('Use the artifact’s recorded sample base path.')
        else:
            standalone = ROOT/'.next/standalone'
            config_path = ROOT/'.next/required-server-files.json'
            if not (standalone/'server.js').is_file() or not config_path.is_file():
                parser.error('Run the sample build first.')
            config = json.loads(config_path.read_text())['config']
            if config.get('basePath', '') != args.base_path or config.get('env', {}).get('NEXT_PUBLIC_SAMPLE_MODE') != '1':
                parser.error('Rebuild sample mode with the same base path before starting.')
        env.update(HOSTNAME=args.hostname, PORT=str(args.port))
        return subprocess.call([node, str(standalone/'server.js')], cwd=standalone, env=env)
    cli = ROOT/'node_modules/next/dist/bin/next'
    if not cli.is_file():
        parser.error('Run npm ci in the repository root first.')
    command = [node, str(cli), args.action, "--webpack"]
    if args.action == 'dev':
        command += ['--hostname', args.hostname, '--port', str(args.port)]
    result = subprocess.call(command, cwd=ROOT, env=env)
    if result == 0 and args.action == 'build':
        standalone = ROOT/'.next/standalone'
        if not (standalone/'server.js').is_file():
            parser.error('The standalone build did not produce its server.')
        for source, target in [(ROOT/'public', standalone/'public'), (ROOT/'.next/static', standalone/'.next/static')]:
            shutil.copytree(source, target, dirs_exist_ok=True)
        (standalone/'tools').mkdir(exist_ok=True)
        shutil.copy2(Path(__file__).resolve(), standalone/'tools/sample-app.py')
        (standalone/'sample-runtime.json').write_text(json.dumps({
            'schema': 1, 'mode': 'sample', 'basePath': args.base_path,
            'node': '22.18+ in the Node 22 line', 'providers_enabled': False,
        }, indent=2)+'\n')
        for name in ['LICENSE', 'THIRD-PARTY-NOTICES.md']:
            source=SOURCE_ROOT/name
            if source.is_file():shutil.copy2(source, standalone/name)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
