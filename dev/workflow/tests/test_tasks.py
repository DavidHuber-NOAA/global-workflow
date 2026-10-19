from rocoto.tasks import Tasks


class TestTasks:

    '''
    Tasks class tests

    Note: this is currently only testing a small fraction of the class.
    '''

    def test_job_groups(self):
        test_array = list(range(0, 24))

        # Test simple splitting with no breakpoints
        test_groups = [{'fhrs': [0, 1, 2, 3, 4, 5], 'seg': 0},
                       {'fhrs': [6, 7, 8, 9, 10, 11], 'seg': 0},
                       {'fhrs': [12, 13, 14, 15, 16, 17], 'seg': 0},
                       {'fhrs': [18, 19, 20, 21, 22, 23], 'seg': 0}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=4) == test_groups

        # Test with a break point that aligns with normal split point
        test_groups = [{'fhrs': [0, 1, 2, 3, 4, 5], 'seg': 0},
                       {'fhrs': [6, 7, 8, 9, 10, 11], 'seg': 0},
                       {'fhrs': [12, 13, 14, 15, 16, 17], 'seg': 1},
                       {'fhrs': [18, 19, 20, 21, 22, 23], 'seg': 1}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=4, breakpoints=[11]) == test_groups

        # Test with a break point not at a normal split point
        test_groups = [{'fhrs': [0, 1, 2, 3, 4, 5, 6, 7], 'seg': 0},
                       {'fhrs': [8, 9, 10, 11, 12, 13, 14], 'seg': 0},
                       {'fhrs': [15, 16, 17, 18, 19], 'seg': 1},
                       {'fhrs': [20, 21, 22, 23], 'seg': 1}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=4, breakpoints=[14]) == test_groups

        # Test highly skewed break point
        test_groups = [{'fhrs': [0, 1, 2, 3, 4, 5, 6, 7], 'seg': 0},
                       {'fhrs': [8, 9, 10, 11, 12, 13, 14, 15], 'seg': 0},
                       {'fhrs': [16, 17, 18, 19, 20, 21, 22], 'seg': 0},
                       {'fhrs': [23], 'seg': 1}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=4, breakpoints=[22]) == test_groups

        # Test with two break points that align
        test_groups = [{'fhrs': [0, 1, 2, 3, 4, 5], 'seg': 0},
                       {'fhrs': [6, 7, 8, 9, 10, 11], 'seg': 0},
                       {'fhrs': [12, 13, 14, 15, 16, 17], 'seg': 1},
                       {'fhrs': [18, 19, 20, 21, 22, 23], 'seg': 2}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=4, breakpoints=[11, 17]) == test_groups

        # Test with two skewed break points
        test_groups = [{'fhrs': [0, 1], 'seg': 0},
                       {'fhrs': [2, 3, 4, 5, 6, 7], 'seg': 1},
                       {'fhrs': [8, 9, 10, 11, 12], 'seg': 1},
                       {'fhrs': [13, 14, 15, 16, 17], 'seg': 1},
                       {'fhrs': [18, 19, 20, 21, 22], 'seg': 1},
                       {'fhrs': [23], 'seg': 2}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=6, breakpoints=[1, 22]) == test_groups

        # Test slightly irregular break points
        test_groups = [{'fhrs': [0, 1, 2, 3], 'seg': 0},
                       {'fhrs': [4, 5, 6], 'seg': 0},
                       {'fhrs': [7, 8, 9, 10], 'seg': 1},
                       {'fhrs': [11, 12, 13, 14], 'seg': 1},
                       {'fhrs': [15, 16, 17, 18], 'seg': 1},
                       {'fhrs': [19, 20, 21, 22, 23], 'seg': 2}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=6, breakpoints=[6, 18]) == test_groups

        # Test more groups than fhrs available
        test_array = list(range(0, 6))
        test_groups = [{'fhrs': [0], 'seg': 0},
                       {'fhrs': [1], 'seg': 0},
                       {'fhrs': [2], 'seg': 0},
                       {'fhrs': [3], 'seg': 0},
                       {'fhrs': [4], 'seg': 0},
                       {'fhrs': [5], 'seg': 0}]
        assert Tasks.get_job_groups(fhrs=test_array, ngroups=15) == test_groups

    def test_multiply_HMS(self):
        assert Tasks.multiply_HMS('00:10:00', 2) == '00:20:00'
        assert Tasks.multiply_HMS('00:30:00', 10) == '05:00:00'
        assert Tasks.multiply_HMS('01:15:00', 4) == '05:00:00'
        assert Tasks.multiply_HMS('00:05:00', 1.5) == '00:07:30'
        assert Tasks.multiply_HMS('00:40:00', 2.5) == '01:40:00'
        assert Tasks.multiply_HMS('00:10:00', 1) == '00:10:00'

    @staticmethod
    def _resource_for(scheduler, **overrides):
        """Build a bare Tasks object and return get_resource('atmos_products') for it."""
        from types import SimpleNamespace

        task = object.__new__(Tasks)
        task.app_config = SimpleNamespace(scheduler=scheduler)
        task._base = {'DEBUG_POSTSCRIPT': False}
        for attr in ['queue_service', 'partition_service', 'clusters_service', 'constraint_service',
                     'queue_exclusive', 'partition_exclusive', 'clusters_exclusive', 'constraint_exclusive',
                     'queue_dtn', 'partition_dtn', 'clusters_dtn', 'constraint_dtn',
                     'partition_batch', 'clusters_batch', 'constraint_batch', 'reservation_batch']:
            setattr(task, attr, None)
        task.queue_batch = 'dev'
        config = {'ACCOUNT': 'acct', 'walltime': '00:15:00', 'ntasks': 24, 'tasks_per_node': 24,
                  'threads_per_task': 1, 'PARTITION_BATCH': None}
        config.update(overrides)
        task._configs = {'atmos_products': config}
        return task.get_resource('atmos_products')

    def test_prepost_resources(self):
        # Product jobs on the WCOSS2 prepost nodes: shared, explicit memory, prepost flag
        resource = self._resource_for('pbspro', memory='6GB', prepost=True, is_exclusive=False)
        assert resource['memory'] == '6GB:prepost=true'
        assert resource['native'] == '-l place=vscatter:shared'

        # PBS jobs without the prepost flag are unchanged
        resource = self._resource_for('pbspro', memory='6GB')
        assert resource['memory'] == '6GB'

        # Slurm XMLs are unchanged by the prepost flag
        resource = self._resource_for('slurm', memory='6GB', prepost=True)
        assert resource['memory'] == '6GB'
        assert 'prepost' not in resource['native']
