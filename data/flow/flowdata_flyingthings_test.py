import os
import os.path
import tensorflow as tf
import unittest
from data.flow.flowdata import FlowDataSet
from data.flow.flowdata_test_base import TestFlowDataSet
from utils.data import silently_remove_file


class FlyingThingsTestPaths:
    train_c_directory = os.path.join('data', 'flow', 'test_data', 'flying_things', 'frames_cleanpass', 'TRAIN', 'C')
    full_img_directory_0 = os.path.join(train_c_directory, '0000', 'left')
    full_flow_directory_0 = os.path.join(train_c_directory, '0000', 'left')
    full_img_directory_1 = os.path.join(train_c_directory, '0001', 'left')
    full_flow_directory_1 = os.path.join(train_c_directory, '0001', 'left')
    expected_image_a_paths = [os.path.join(full_img_directory_0, '0006.png'),
                              os.path.join(full_img_directory_0, '0007.png'),
                              os.path.join(full_img_directory_0, '0008.png'),
                              os.path.join(full_img_directory_0, '0009.png'),
                              os.path.join(full_img_directory_1, '0006.png')]
    expected_image_b_paths = [os.path.join(full_img_directory_0, '0007.png'),
                              os.path.join(full_img_directory_0, '0008.png'),
                              os.path.join(full_img_directory_0, '0009.png'),
                              os.path.join(full_img_directory_0, '0010.png'),
                              os.path.join(full_img_directory_1, '0007.png')]
    expected_flow_paths = [os.path.join(full_flow_directory_0, 'OpticalFlowIntoFuture_0006_L.pfm'),
                           os.path.join(full_flow_directory_0, 'OpticalFlowIntoFuture_0007_L.pfm'),
                           os.path.join(full_flow_directory_0, 'OpticalFlowIntoFuture_0008_L.pfm'),
                           os.path.join(full_flow_directory_0, 'OpticalFlowIntoFuture_0009_L.pfm'),
                           os.path.join(full_flow_directory_1, 'OpticalFlowIntoFuture_0006_L.pfm')]


class TestFlyingThingsFlowDataSet(TestFlowDataSet.TestCases):
    def setUp(self):
        super().setUp()

        data_directory = os.path.join('data', 'flow', 'test_data', 'flying_things')
        self.resolution = [540, 960]
        # No data augmentation so that the tests are deterministic.
        self.data_set = FlowDataSet(data_directory, batch_size=2, validation_size=1, training_augmentations=False,
                                    data_source=FlowDataSet.FLYING_THINGS)

        # Test paths.
        self.expected_image_a_paths = FlyingThingsTestPaths.expected_image_a_paths
        self.expected_image_b_paths = FlyingThingsTestPaths.expected_image_b_paths
        self.expected_flow_paths = FlyingThingsTestPaths.expected_flow_paths


class TestFlyingThingsFlowDataSetWithCrop(TestFlowDataSet.TestCases):
    def setUp(self):
        super().setUp()

        data_directory = os.path.join('data', 'flow', 'test_data', 'flying_things')
        self.resolution = [384, 448]
        # No data augmentation so that the tests are deterministic.
        self.data_set = FlowDataSet(data_directory, batch_size=2, validation_size=1, training_augmentations=False,
                                    data_source=FlowDataSet.FLYING_THINGS, crop_size=(384, 448))

        # Test paths.
        self.expected_image_a_paths = FlyingThingsTestPaths.expected_image_a_paths
        self.expected_image_b_paths = FlyingThingsTestPaths.expected_image_b_paths
        self.expected_flow_paths = FlyingThingsTestPaths.expected_flow_paths


class TestFlyingThingsDataSetMaxFlow(unittest.TestCase):
    def setUp(self):
        # FlowData data set.
        data_directory = os.path.join('data', 'flow', 'test_data', 'flying_things')
        self.data_set = FlowDataSet(data_directory, batch_size=2, validation_size=1, training_augmentations=False,
                                    data_source=FlowDataSet.FLYING_THINGS, max_flow=1)

        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        self.sess = tf.Session(config=config)

    def test_no_outputs(self):
        self.data_set.preprocess_raw(shard_size=2)
        output_paths = self.data_set.get_train_file_names() + self.data_set.get_validation_file_names()
        self.assertEqual(0, len(output_paths))

    def tearDown(self):
        # In case the test failed, clean up.
        output_paths = self.data_set.get_train_file_names() + self.data_set.get_validation_file_names()
        for output_path in output_paths:
            silently_remove_file(output_path)


if __name__ == '__main__':
    unittest.main()
