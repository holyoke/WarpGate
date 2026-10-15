import unittest
import json
from unittest.mock import patch
import agent


class ReleaseTests(unittest.TestCase):
    def run_record(self, **values):
        result = dict(status='completed', conclusion='success', event='push', head_branch='master',
                      head_repository={'full_name': 'holyoke/WarpGate'}, head_sha='a' * 40)
        result.update(values)
        return result

    def test_only_successful_trusted_branch_releases(self):
        for change in [dict(conclusion='failure'), dict(status='in_progress'),
                       dict(event='pull_request'), dict(head_branch='feature'),
                       dict(head_repository={'full_name': 'someone/fork'}), dict(head_sha='../latest')]:
            with self.subTest(change=change):
                self.assertIsNone(agent.select_release([self.run_record(**change)]))

    def test_manual_run_can_be_deployed(self):
        run = self.run_record(event='workflow_dispatch')
        self.assertEqual(agent.select_release([run]), run)

    def test_chained_release_uses_built_revision_instead_of_default_branch_head(self):
        run = self.run_record(event='workflow_run', head_sha='b' * 40,
                              display_title='WarpGate release 123 ' + 'a' * 40)
        release = agent.select_release([run])
        self.assertEqual(release['head_sha'], 'a' * 40)
        self.assertEqual(release['source_run_id'], 123)
        self.assertIsNone(agent.select_release([{**run, 'display_title': 'WarpGate release 123 latest'}]))

    def test_chained_release_checks_upstream_repository_workflow_and_sha(self):
        for change in [{}, {'path': '.github/workflows/other.yml'}, {'head_sha': 'b' * 40},
                       {'conclusion': 'failure'}, {'head_repository': {'full_name': 'someone/fork'}}]:
            with self.subTest(change=change):
                agent.trusted_source.cache_clear()
                source = self.run_record(path='.github/workflows/deploy.yml', **change) if 'path' not in change else self.run_record(**change)
                with patch.object(agent, 'http', return_value=(json.dumps(source).encode(), {})):
                    self.assertEqual(agent.trusted_source(123, 'a' * 40), not change)

    def test_rollout_requires_observed_generation_and_availability(self):
        deployment = {'spec': {'replicas': 1}, 'status': {
            'observedGeneration': 3, 'updatedReplicas': 1, 'availableReplicas': 1}}
        self.assertTrue(agent.ready(deployment, 3))
        self.assertFalse(agent.ready(deployment, 4))
        deployment['status']['availableReplicas'] = 0
        self.assertFalse(agent.ready(deployment, 3))

    def test_failed_rollout_restores_previous_image(self):
        release = self.run_record(id=10, run_attempt=1, html_url='https://github.com/example/run')
        deployment = {'metadata': {'annotations': {}}, 'spec': {'template': {'spec': {
            'containers': [{'name': 'warpgate', 'image': 'old-image'}]}}}}
        with patch.object(agent, 'latest_release', return_value=release), \
                patch.object(agent, 'image_digest', return_value='new-image'), \
                patch.object(agent, 'await_ready', side_effect=[TimeoutError('test'), None]), \
                patch.object(agent, 'kube', side_effect=[deployment, {'metadata': {'generation': 2}},
                    {}, {'metadata': {'generation': 3}}]) as kube:
            with self.assertLogs(agent.LOG, level='ERROR'), self.assertRaises(TimeoutError):
                agent.reconcile()
            self.assertEqual(kube.call_args_list[1].kwargs['patch'], agent.image_patch('new-image'))
            self.assertEqual(kube.call_args_list[3].kwargs['patch'], agent.image_patch('old-image'))

    def test_restart_during_rollout_still_waits_for_readiness(self):
        release = self.run_record(id=10, run_attempt=1, html_url='https://github.com/example/run')
        deployment = {'metadata': {'generation': 3, 'annotations': {}}, 'spec': {'template': {'spec': {
            'containers': [{'name': 'warpgate', 'image': 'new-image'}]}}}}
        with patch.object(agent, 'latest_release', return_value=release), \
                patch.object(agent, 'image_digest', return_value='new-image'), \
                patch.object(agent, 'await_ready') as await_ready, \
                patch.object(agent, 'kube', side_effect=[deployment, {}]):
            agent.reconcile()
            await_ready.assert_called_once_with(3)


if __name__ == '__main__':
    unittest.main()
