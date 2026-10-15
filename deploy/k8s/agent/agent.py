"""Namespace-scoped, pull-based deployment of successful WarpGate CI releases."""
import hashlib
import json
import logging
import os
import re
import signal
import ssl
import sys
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

LOG = logging.getLogger('warpgate-release')
REPO = os.environ.get('GITHUB_REPOSITORY', 'holyoke/WarpGate')
WORKFLOW = os.environ.get('GITHUB_WORKFLOW', 'cluster-release.yml')
BRANCH = os.environ.get('GITHUB_BRANCH', 'master')
PACKAGE = os.environ.get('IMAGE_REPOSITORY', 'holyoke/warpgate')
NAMESPACE = os.environ.get('NAMESPACE', 'warpgate')
DEPLOYMENT = os.environ.get('TARGET_DEPLOYMENT', 'warpgate')
TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'
CA_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
HEARTBEAT = '/tmp/agent-heartbeat'
PREFIX = 'warpgate.io/'


def heartbeat():
    Path(HEARTBEAT).touch()


def http(url, data=None, headers=None, context=None, method=None):
    req = urllib.request.Request(url, data, headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=30, context=context) as response:
        return response.read(), dict(response.headers)


def kube(path='', patch=None):
    # Read projected tokens for every request so token rotation is respected.
    headers = {'Authorization': 'Bearer ' + Path(TOKEN_PATH).read_text().strip()}
    data = None
    if patch is not None:
        headers['Content-Type'] = 'application/strategic-merge-patch+json'
        data = json.dumps(patch).encode()
    context = ssl.create_default_context(cafile=CA_PATH)
    raw, _ = http(
        f'https://kubernetes.default.svc/apis/apps/v1/namespaces/{NAMESPACE}/deployments/{DEPLOYMENT}{path}',
        data, headers, context, 'PATCH' if patch is not None else 'GET',
    )
    return json.loads(raw)


def select_release(runs):
    for run in runs:
        if (run.get('status') == 'completed' and run.get('conclusion') == 'success'
                and run.get('event') in ('push', 'workflow_dispatch', 'workflow_run')
                and run.get('head_branch') == BRANCH
                and run.get('head_repository', {}).get('full_name', '').lower() == REPO.lower()
                and re.fullmatch(r'[0-9a-f]{40}', run.get('head_sha', ''))):
            if run.get('event') == 'workflow_run':
                # workflow_run.head_sha is the default-branch HEAD, not necessarily
                # the commit built by its upstream CI. Use the explicit source ID/SHA.
                match = re.fullmatch(r'WarpGate release ([1-9][0-9]*) ([0-9a-f]{40})', run.get('display_title', ''))
                if not match:
                    continue
                return {**run, 'source_run_id': int(match[1]), 'head_sha': match[2]}
            return run
    return None


@lru_cache(maxsize=64)
def trusted_source(run_id, revision):
    raw, _ = http(f'https://api.github.com/repos/{REPO}/actions/runs/{run_id}',
                  headers={'User-Agent': 'WarpGate-Release-Agent', 'Accept': 'application/vnd.github+json'})
    source = json.loads(raw)
    return (source.get('path') == '.github/workflows/deploy.yml'
            and source.get('event') in ('push', 'workflow_dispatch')
            and source.get('head_sha') == revision
            and select_release([source]) is not None)


def latest_release():
    query = urllib.parse.urlencode({'branch': BRANCH, 'status': 'success', 'per_page': 10})
    url = f'https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?{query}'
    raw, _ = http(url, headers={'User-Agent': 'WarpGate-Release-Agent', 'Accept': 'application/vnd.github+json'})
    runs = json.loads(raw).get('workflow_runs', [])
    for run in runs:
        release = select_release([run])
        if release and (release.get('event') != 'workflow_run'
                        or trusted_source(release['source_run_id'], release['head_sha'])):
            return release
    return None


def image_digest(revision):
    scope = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': f'repository:{PACKAGE}:pull'})
    raw, _ = http('https://ghcr.io/token?' + scope)
    token = json.loads(raw)['token']
    raw, headers = http(f'https://ghcr.io/v2/{PACKAGE}/manifests/{revision}', headers={
        'Authorization': 'Bearer ' + token,
        'Accept': ', '.join([
            'application/vnd.oci.image.manifest.v1+json',
            'application/vnd.oci.image.index.v1+json',
            'application/vnd.docker.distribution.manifest.v2+json',
        ]),
    })
    headers = {key.lower(): value for key, value in headers.items()}
    digest = headers.get('docker-content-digest', 'sha256:' + hashlib.sha256(raw).hexdigest())
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Registry returned an invalid manifest digest')
    return f'ghcr.io/{PACKAGE}@{digest}'


def annotations(deployment):
    return deployment.get('metadata', {}).get('annotations', {})


def current_image(deployment):
    return next(container['image'] for container in deployment['spec']['template']['spec']['containers']
                if container['name'] == 'warpgate')


def image_patch(image):
    return {'spec': {'template': {'spec': {
        'containers': [{'name': 'warpgate', 'image': image}],
        'initContainers': [{'name': 'wait-postgres', 'image': image}],
    }}}}


def ready(deployment, generation):
    status = deployment.get('status', {})
    replicas = deployment['spec'].get('replicas', 1)
    return (status.get('observedGeneration', 0) >= generation
            and status.get('updatedReplicas', 0) == replicas
            and status.get('availableReplicas', 0) == replicas
            and status.get('unavailableReplicas', 0) == 0)


def await_ready(generation):
    deadline = time.monotonic() + int(os.environ.get('ROLLOUT_TIMEOUT_SECONDS', '600'))
    while time.monotonic() < deadline:
        heartbeat()
        if ready(kube(), generation):
            raw, _ = http(f'http://warpgate.{NAMESPACE}.svc:8080/health')
            if json.loads(raw).get('status') == 'ok':
                return
        time.sleep(5)
    raise TimeoutError('Application rollout did not become healthy')


def reconcile():
    release = latest_release()
    if release is None:
        LOG.info('No successful eligible workflow run yet')
        return
    revision = release['head_sha']
    run_key = f"{release['id']}:{release.get('run_attempt', 1)}"
    deployment = kube()
    state = annotations(deployment)
    old_image = current_image(deployment)
    if (state.get(PREFIX + 'revision') == revision
            and state.get(PREFIX + 'image') == old_image):
        LOG.info('Already deployed %s', revision[:12])
        return
    if state.get(PREFIX + 'failed-run') == run_key:
        LOG.warning('Run %s previously failed; awaiting a newer run', run_key)
        return
    target_image = image_digest(revision)
    LOG.info('Reconciling successful run %s: %s', run_key, revision)
    previous_image = old_image if old_image != target_image else state.get(PREFIX + 'image', old_image)
    try:
        if old_image != target_image:
            updated = kube(patch=image_patch(target_image))
        else:
            updated = deployment
        await_ready(updated['metadata']['generation'])
    except Exception:
        LOG.exception('Rollout failed; attempting previous application image')
        kube(patch={'metadata': {'annotations': {PREFIX + 'failed-run': run_key}}})
        if previous_image != target_image:
            restored = kube(patch=image_patch(previous_image))
            await_ready(restored['metadata']['generation'])
        raise
    kube(patch={'metadata': {'annotations': {
        PREFIX + 'revision': revision,
        PREFIX + 'image': target_image,
        PREFIX + 'run-url': release['html_url'],
        PREFIX + 'deployed-at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        PREFIX + 'failed-run': None,
    }}})
    LOG.info('Deployment healthy: %s (%s)', revision, target_image)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    interval = max(120, int(os.environ.get('POLL_INTERVAL_SECONDS', '120')))
    while True:
        heartbeat()
        try:
            reconcile()
        except Exception:
            LOG.exception('Release reconciliation failed; will retry')
        heartbeat()
        time.sleep(interval)


if __name__ == '__main__':
    main()
