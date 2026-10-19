"""Offline safety checks: never starts Docker or connects to Kubernetes."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).with_name('install.py'))
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def cluster_args(self, **overrides):
        values = dict(namespace='example', image='example/app@sha256:123',
                      storage_class=None, node_port=30489, dry_run=False,
                      kubeconfig=None, context=None, timeout=20,
                      admin_email='admin@example.com')
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_portable_manifest_and_image_consistency(self):
        manifest = installer.cluster_manifest(self.cluster_args())
        for item in manifest['items']:
            self.assertEqual(item['metadata']['namespace'], 'example')
            if item['kind'] == 'PersistentVolumeClaim':
                self.assertNotIn('storageClassName', item['spec'])
            if item['kind'] == 'Deployment':
                pod = item['spec']['template']['spec']
                self.assertNotIn('nodeSelector', pod)
                if item['metadata']['name'] == 'warpgate':
                    self.assertEqual(pod['containers'][0]['image'], 'example/app@sha256:123')
                    self.assertEqual(pod['initContainers'][0]['image'], 'example/app@sha256:123')
        self.assertNotIn('release-agent', json.dumps(manifest))

    def test_dry_run_never_calls_external_tools_or_generates_secrets(self):
        with patch.object(installer, 'run') as run, patch.object(installer, 'new_credentials') as new:
            with contextlib.redirect_stdout(io.StringIO()):
                installer.main(['k8s', '--dry-run', '--kubeconfig', 'does-not-exist'])
                installer.main(['local', '--dry-run'])
            run.assert_not_called()
            new.assert_not_called()

    def test_secret_read_failure_stops_before_workloads_or_new_credentials(self):
        def fake_run(command, payload=None, capture=False):
            if 'secret' in command:
                raise RuntimeError('access denied')
            return ''
        with patch.object(installer, 'run', side_effect=fake_run) as run:
            with patch.object(installer, 'new_credentials') as new:
                with self.assertRaisesRegex(RuntimeError, 'access denied'):
                    installer.k8s(self.cluster_args())
                new.assert_not_called()
                self.assertEqual(run.call_count, 2)  # namespace then read, nothing else

    def test_existing_secret_and_pvcs_are_not_overwritten(self):
        applied = []

        def fake_run(command, payload=None, capture=False):
            if payload:
                applied.append(json.loads(payload))
            if 'secret' in command:
                return json.dumps({'data': dict.fromkeys(installer.SECRET_KEYS, 'existing')})
            if 'pvc' in command:
                return 'persistentvolumeclaim/existing'
            return ''

        with patch.object(installer, 'run', side_effect=fake_run):
            with patch.object(installer, 'new_credentials') as new:
                with contextlib.redirect_stdout(io.StringIO()):
                    installer.k8s(self.cluster_args(storage_class='another-class'))
                new.assert_not_called()
        self.assertEqual(applied[0]['kind'], 'Namespace')
        self.assertTrue(applied[1]['items'])
        self.assertFalse(any(i['kind'] in ('PersistentVolumeClaim', 'Secret')
                             for i in applied[1]['items']))

    def test_local_reinstall_preserves_credentials_and_overrides_external_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            values = dict.fromkeys(installer.SECRET_KEYS, 'existing-secret')
            values.update(ADMIN_EMAIL='admin@example.com', APP_IMAGE='old-image',
                          BIND_HOST='127.0.0.1', SERVER_PORT='8081')
            installer.private_write(directory / '.env', ''.join(
                f'{key}={value}\n' for key, value in values.items()))
            observed = []

            def fake_run(command, payload=None, capture=False):
                if 'up' in command:
                    observed.append(os.environ['POSTGRES_PASSWORD'])
                return ''

            with patch.dict(os.environ, {'POSTGRES_PASSWORD': 'wrong-external-password'}):
                with patch.object(installer, 'run', side_effect=fake_run):
                    with patch.object(installer, 'new_credentials') as new:
                        with contextlib.redirect_stdout(io.StringIO()):
                            installer.main(['local', '--data-dir', str(directory),
                                            '--image', 'new-image'])
                        new.assert_not_called()
                self.assertEqual(os.environ['POSTGRES_PASSWORD'], 'wrong-external-password')
            after = installer.read_env(directory / '.env')
            self.assertEqual(observed, ['existing-secret'])
            for key in installer.SECRET_KEYS:
                self.assertEqual(after[key], values[key])
            self.assertEqual(after['SERVER_PORT'], '8081')
            self.assertEqual(after['APP_IMAGE'], 'new-image')

    def test_local_failure_does_not_record_successful_upgrade(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            values = dict.fromkeys(installer.SECRET_KEYS, 'existing')
            values['APP_IMAGE'] = 'old-image'
            installer.private_write(directory / '.env', ''.join(
                f'{key}={value}\n' for key, value in values.items()))

            def fake_run(command, payload=None, capture=False):
                if 'up' in command:
                    raise RuntimeError('not healthy')
                return ''

            with patch.object(installer, 'run', side_effect=fake_run):
                with self.assertRaises(SystemExit) as stopped:
                    installer.main(['local', '--data-dir', str(directory), '--image', 'new-image'])
            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual(installer.read_env(directory / '.env')['APP_IMAGE'], 'old-image')

    def test_first_cluster_install_creates_secret_without_printing_password(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            applied = []

            def fake_run(command, payload=None, capture=False):
                if payload:
                    applied.append(json.loads(payload))
                return ''

            # Template lookup uses ROOT as well, so keep the real render function.
            rendered = installer.cluster_manifest(self.cluster_args())
            output = io.StringIO()
            with patch.object(installer, 'ROOT', root):
                with patch.object(installer, 'cluster_manifest', return_value=rendered):
                    with patch.object(installer, 'run', side_effect=fake_run):
                        with contextlib.redirect_stdout(output):
                            installer.k8s(self.cluster_args())
            secret = next(item for item in applied if item['kind'] == 'Secret')
            password = secret['stringData']['ADMIN_PASSWORD']
            record = root / '.local/install-example-admin.txt'
            self.assertIn(password, record.read_text())
            self.assertNotIn(password, output.getvalue())
            self.assertEqual(set(secret['stringData']), set(installer.SECRET_KEYS))

    def test_first_local_install_is_repeatable(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = ['local', '--data-dir', temporary, '--port', '18080']
            with patch.object(installer, 'run', return_value=''):
                with contextlib.redirect_stdout(io.StringIO()):
                    installer.main(args)
                    before = (Path(temporary) / '.env').read_bytes()
                    installer.main(args)
            self.assertEqual(before, (Path(temporary) / '.env').read_bytes())
            self.assertEqual(installer.read_env(Path(temporary) / '.env')['SERVER_PORT'], '18080')


if __name__ == '__main__':
    unittest.main()
