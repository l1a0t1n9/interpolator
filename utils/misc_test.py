import json
import unittest
from utils.misc import *


class TestMiscUtils(unittest.TestCase):
    def setUp(self):
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        self.sess = tf.Session(config=config)

    def test_sliding_window_slice_dense(self):
        x = tf.constant([
            [0, 0],
            [0, 1],
            [1, 0],
        ])
        expected = [
            [[0, 0], [0, 1]],
            [[0, 1], [1, 0]]
        ]
        slice_locations = [1, 1]
        sliced = sliding_window_slice(x, slice_locations)
        sliced_list = self.sess.run(sliced).tolist()
        self.assertListEqual(sliced_list, expected)

    def test_sliding_window_slice_sparse(self):
        x = tf.constant([
            [0, 0],
            [1, 1],
            [0, 0],
            [2, 2],
            [0, 0],
            [3, 3],
        ])
        expected = [
            [[0, 0], [0, 0], [0, 0]],
            [[1, 1], [2, 2], [3, 3]]
        ]
        slice_locations = [1, 0, 1, 0, 1]
        sliced = sliding_window_slice(x, slice_locations)
        sliced_list = self.sess.run(sliced).tolist()
        self.assertListEqual(sliced_list, expected)

    def test_sliding_window_slice_small(self):
        x = tf.constant([
            [1, 2.4]
        ])
        expected = [
            [[0, 0], [0, 0], [0, 0]]
        ]
        slice_locations = [1, 1, 1]
        sliced = sliding_window_slice(x, slice_locations)
        sliced_list = self.sess.run(sliced).tolist()
        self.assertListEqual(sliced_list, expected)


class TestPreprocessVarRefs(unittest.TestCase):
    def test_no_change(self):
        json_str = """
        {
            "one": 1,
            "two": 2,
            "three": 3,
            "array": [ 1, 2, 3 ]
        }
        """
        self.jsonEquals(json_str, json_str)

    def test_basic_change(self):
        json_str = """
        {
            "vars": {
                "two": 2
            },
            "one": 1,
            "two": { "var_ref": "two" },
            "three": 3
        }
        """
        expected_json_str = """
        {
            "one": 1,
            "two": 2,
            "three": 3
        }
        """
        self.jsonEquals(json_str, expected_json_str)

    def test_recursive_change(self):
        json_str = """
        {
            "vars": {
                "foo": "bar",
                "two": 2
            },
            "obj": {
                "moop": { "var_ref": "foo" },
                "boop": { "var_ref": "two" }
            },
            "boop": { "var_ref": "foo" }
        }
        """
        expected_json_str = """
        {
            "obj": {
                "moop": "bar",
                "boop": 2
            },
            "boop": "bar"
        }
        """
        self.jsonEquals(json_str, expected_json_str)

    def test_recursive_override(self):
        json_str = """
        {
            "vars": {
                "foo": "bar",
                "two": 2
            },
            "obj": {
                "vars": {
                    "foo": "not bar"
                },
                "moop": { "var_ref": "foo" },
                "boop": { "var_ref": "two" }
            },
            "boop": { "var_ref": "foo" }
        }
        """
        expected_json_str = """
        {
            "obj": {
                "moop": "not bar",
                "boop": 2
            },
            "boop": "bar"
        }
        """
        self.jsonEquals(json_str, expected_json_str)

    def test_list_changes(self):
        json_str = """
        {
            "vars": {
                "foo": "bar",
                "two": 2
            },
            "obj": {
                "vars": {
                    "foo": "not bar",
                    "other_var": 3.14
                },
                "moop": [
                    {
                        "recursive": { "var_ref": "foo" }
                    },
                    { "var_ref": "other_var" }
                ]
            },
            "boop": [
                { "var_ref": "foo" },
                2
            ]
        }
        """
        expected_json_str = """
        {
            "obj": {
                "moop": [
                    {
                        "recursive": "not bar"
                    },
                    3.14
                ]
            },
            "boop": [
                "bar",
                2
            ]
        }
        """
        self.jsonEquals(json_str, expected_json_str)

    def jsonEquals(self, json_str, expected_json_str):
        content = json.loads(json_str)
        expected_content = json.loads(expected_json_str)
        preprocess_var_refs(content)
        self.assertDictEqual(expected_content, content)


if __name__ == '__main__':
    unittest.main()
