import time
from unittest import TestCase

from pcs.common import tools


class TestException(Exception):
    pass

class RunParallelTestCase(TestCase):
    def test_run_all(self):
        data_list = [([i], {}) for i in range(5)]
        out_list = []
        tools.run_parallel(out_list.append, data_list)
        self.assertEqual(sorted(out_list), [i for i in range(5)])

    def test_parallelism(self):
        timeout = 5
        data_list = [[[i + 1], {}] for i in range(timeout)]
        start_time = time.time()
        # this should last for least timeout seconds, but less than sum of all
        # times
        tools.run_parallel(time.sleep, data_list)
        finish_time = time.time()
        elapsed_time = finish_time - start_time
        self.assertTrue(elapsed_time > timeout)
        self.assertTrue(elapsed_time < sum([i + 1 for i in range(timeout)]))


class JoinMultilinesTest(TestCase):
    def test_empty_input(self):
        self.assertEqual(
            "",
            tools.join_multilines([])
        )

    def test_two_strings(self):
        self.assertEqual(
            "a\nb",
            tools.join_multilines(["a", "b"])
        )

    def test_strip(self):
        self.assertEqual(
            "a\nb",
            tools.join_multilines(["  a\n", "  b\n"])
        )

    def test_skip_empty(self):
        self.assertEqual(
            "a\nb",
            tools.join_multilines(["  a\n", "   \n", "  b\n"])
        )

    def test_multiline(self):
        self.assertEqual(
            "a\nA\nb\nB",
            tools.join_multilines(["a\nA\n", "b\nB\n"])
        )
