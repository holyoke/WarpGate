#!/usr/bin/env python3
"""WarpGate installer. Python standard library only; no app build required."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = (ROOT / 'install/release.txt').read_text().strip()
SECRET_KEYS = ('ADMIN_EMAIL', 'ADMIN_PASSWORD', 'POSTGRES_PASSWORD',
               'REDIS_PASSWORD', 'JWT_SECRET', 'TOTP_ENCRYPTION_KEY')


def run(command, payload=None, capture=False):
    result = subprocess.run(command, input=payload, text=True, encoding='utf-8',
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None)
    if result.returncode:
        # Do not echo stderr: tools may include Secret/env payloads in diagnostics.
        raise RuntimeError(f'{command[0]} {command[1]} failed (exit {result.returncode}). '
                           'Check tool access, registry access and resource status.')
    return result.stdout if capture else ''


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting credentials on a repeated install.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)


def new_credentials(email):
    values = {key: secrets.token_hex(32) for key in SECRET_KEYS}
    values.update(ADMIN_EMAIL=email, ADMIN_PASSWORD='WarpGate-' + secrets.token_hex(12))
    return values


def read_env(path):
    return dict(line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.lstrip().startswith('#') and '=' in line)


def local(args):
    directory = args.data_dir.resolve()
    env_path = directory / '.env'
    compose_path = directory / 'compose.yaml'
    command = ['docker', 'compose', '-p', 'warpgate', '--env-file', str(env_path),
               '-f', str(compose_path)]
    if args.dry_run:
        print(f'Local plan: {directory}\nImage: {args.image}\n'
              f'New install URL: http://{args.bind}:{args.port}\n'
              'Reuse existing .env and Docker volumes; validate Compose; wait for health.')
        return
    run(['docker', 'compose', 'version'], capture=True)
    if not env_path.exists():
        values = new_credentials(args.admin_email)
        values.update(APP_IMAGE=args.image, BIND_HOST=args.bind, SERVER_PORT=str(args.port))
        private_write(env_path, ''.join(f'{key}={value}\n' for key, value in values.items()))
    values = read_env(env_path)
    if any(not values.get(key) for key in SECRET_KEYS):
        raise RuntimeError('Existing .env is incomplete. Restore its credentials before retrying.')
    # Separate install state from the old root Compose project's volumes and .env.
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'deploy/compose.server.yaml', compose_path)
    # Process env must not accidentally override the stored database credentials.
    previous = {key: os.environ.get(key) for key in values}
    previous.setdefault('APP_IMAGE', os.environ.get('APP_IMAGE'))
    try:
        os.environ.update(values)
        os.environ['APP_IMAGE'] = args.image
        run(command + ['config', '--quiet'], capture=True)
        run(command + ['up', '-d', '--wait', '--wait-timeout', str(args.timeout)])
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    # Persist only after a successful rollout. Leave credentials untouched.
    values['APP_IMAGE'] = args.image
    env_path.write_text(''.join(f'{key}={value}\n' for key, value in values.items()),
                        encoding='utf-8')
    print(f"Ready: http://{values.get('BIND_HOST', '127.0.0.1')}:{values.get('SERVER_PORT', '8080')}\n"
          f'Initial credentials: {env_path} (ADMIN_EMAIL / ADMIN_PASSWORD)\n'
          f'Manage: docker compose -p warpgate --env-file "{env_path}" -f "{compose_path}" ps')


def cluster_manifest(args):
    manifest = json.loads((ROOT / 'install/kubernetes.json').read_text())
    for item in manifest['items']:
        item['metadata']['namespace'] = args.namespace
        if item['kind'] == 'PersistentVolumeClaim' and args.storage_class:
            item['spec']['storageClassName'] = args.storage_class
        if item['kind'] == 'Deployment' and item['metadata']['name'] == 'warpgate':
            pod = item['spec']['template']['spec']
            pod['containers'][0]['image'] = args.image
            pod['initContainers'][0]['image'] = args.image
        if item['kind'] == 'Service' and item['metadata']['name'] == 'warpgate':
            item['spec']['ports'][0]['nodePort'] = args.node_port
    return manifest


def k8s(args):
    manifest = cluster_manifest(args)
    if args.dry_run:
        # Offline render: no kubectl, no kubeconfig read, no credentials generated.
        print(json.dumps(manifest, indent=2))
        return
    kubectl = ['kubectl']
    if args.kubeconfig:
        if not args.kubeconfig.is_file():
            raise RuntimeError('Kubeconfig file does not exist.')
        kubectl += ['--kubeconfig', str(args.kubeconfig.resolve())]
    if args.context:
        kubectl += ['--context', args.context]
    namespaced = kubectl + ['-n', args.namespace]

    def apply(resource):
        run(kubectl + ['apply', '-f', '-'], json.dumps(resource), capture=True)

    apply({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': args.namespace}})
    existing = run(namespaced + ['get', 'secret', 'warpgate-secrets',
                                '--ignore-not-found', '-o', 'json'], capture=True)
    if existing.strip():
        data = json.loads(existing).get('data', {})
        if any(not data.get(key) for key in SECRET_KEYS):
            raise RuntimeError('Existing warpgate-secrets is incomplete; not replacing credentials.')
    else:
        values = new_credentials(args.admin_email)
        credential_path = ROOT / '.local' / f'install-{args.namespace}-admin.txt'
        # Save before API creation so interruptions cannot lose generated credentials.
        if credential_path.exists():
            raise RuntimeError(f'Credential record already exists: {credential_path}. '
                               'Check its cluster before moving it aside and retrying.')
        private_write(credential_path, '\n'.join(f'{key}={values[key]}'
                                               for key in ('ADMIN_EMAIL', 'ADMIN_PASSWORD')) + '\n')
        run(kubectl + ['create', '-f', '-'], json.dumps({
            'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
            'metadata': {'name': 'warpgate-secrets', 'namespace': args.namespace},
            'stringData': values}), capture=True)
        print(f'Initial credentials: {credential_path}')
    # Never reapply existing PVCs: their storage class and size are deployment-owned.
    items = []
    for item in manifest['items']:
        if item['kind'] == 'PersistentVolumeClaim':
            found = run(namespaced + ['get', 'pvc', item['metadata']['name'],
                                     '--ignore-not-found', '-o', 'name'], capture=True)
            if found.strip():
                continue
        items.append(item)
    apply({'apiVersion': 'v1', 'kind': 'List', 'items': items})
    for name in ('postgres', 'redis', 'warpgate'):
        run(namespaced + ['rollout', 'status', f'deployment/{name}',
                          f'--timeout={args.timeout}s'])
    print(f'Ready: http://<node-ip>:{args.node_port}/home (namespace: {args.namespace})\n'
          'Existing administrator passwords are preserved.\n'
          f'Alternative: kubectl -n {args.namespace} port-forward service/warpgate 18080:8080 '
          '(use the same kubeconfig/context)')


def main(argv=None):
    parser = argparse.ArgumentParser(description='WarpGate: install locally or on Kubernetes.')
    commands = parser.add_subparsers(dest='mode', required=True)
    for mode in ('local', 'k8s'):
        sub = commands.add_parser(mode)
        sub.add_argument('--image', default=DEFAULT_IMAGE, help='Immutable release image recommended')
        sub.add_argument('--admin-email', default='admin@warpgate.local')
        sub.add_argument('--timeout', type=int, default=600, help='Readiness timeout in seconds')
        sub.add_argument('--dry-run', action='store_true', help='Offline plan/render; no changes')
        if mode == 'local':
            sub.add_argument('--data-dir', type=Path, default=ROOT / '.local/install/local')
            sub.add_argument('--bind', default='127.0.0.1')
            sub.add_argument('--port', type=int, default=8080)
        else:
            sub.add_argument('--kubeconfig', type=Path)
            sub.add_argument('--context')
            sub.add_argument('--namespace', default='warpgate')
            sub.add_argument('--storage-class', help='Omit to use the cluster default StorageClass')
            sub.add_argument('--node-port', type=int, default=30488)
    args = parser.parse_args(argv)
    if args.timeout < 1 or not args.image.strip() or any(c.isspace() for c in args.image):
        parser.error('Specify a valid image and positive timeout.')
    if not re.fullmatch(r'[A-Za-z0-9_.+@-]+', args.admin_email) or '@' not in args.admin_email:
        parser.error('Specify a valid administrator email.')
    if args.mode == 'local' and not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535.')
    if args.mode == 'k8s':
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', args.namespace):
            parser.error('Use a Kubernetes DNS label for --namespace (max 63 characters).')
        if not 30000 <= args.node_port <= 32767:
            parser.error('--node-port must be between 30000 and 32767.')
    try:
        (local if args.mode == 'local' else k8s)(args)
    except (RuntimeError, OSError, ValueError) as error:
        parser.exit(1, f'Installation stopped: {error}\n')


if __name__ == '__main__':
    main()
