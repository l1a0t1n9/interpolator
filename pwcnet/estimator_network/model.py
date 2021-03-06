import tensorflow as tf
from common.models import ConvNetwork
from common.utils.tf import leaky_relu
from pwcnet.cost_volume.cost_volume import cost_volume
from pwcnet.warp.warp import backward_warp


class EstimatorNetwork(ConvNetwork):
    def __init__(self, name='estimator_network', layer_specs=None,
                 activation_fn=leaky_relu,
                 regularizer=None, search_range=4, dense_net=True, cost_volume_activation=True):
        """
        :param name: Str. For variable scoping.
        :param layer_specs: See parent class.
        :param activation_fn: Tensorflow activation function.
        :param regularizer: Tf regularizer such as tf.contrib.layers.l2_regularizer.
        :param dense_net: Bool. Default for PWC-Net is true.
        :param cost_volume_activation: Bool. Whether to put an activation function on the cost volume.
        """
        if layer_specs is None:
            # PWC-Net default.
            layer_specs = [[3, 128, 1, 1],
                           [3, 128, 1, 1],
                           [3, 96, 1, 1],
                           [3, 64, 1, 1],
                           [3, 32, 1, 1],
                           [3, 2, 1, 1]]  # last_activation_fn is linear.

        super().__init__(name=name, layer_specs=layer_specs,
                         activation_fn=activation_fn, last_activation_fn=None,
                         regularizer=regularizer, padding='SAME', dense_net=dense_net)

        self.search_range = search_range
        self.cost_volume_activation = cost_volume_activation

    def get_forward(self, features1, features2, optical_flow, previous_estimator_feature,
                    pre_warp_scaling=1.0, reuse_variables=tf.AUTO_REUSE):
        """
        features1   features2  optical_flow  previous_estimator_feature
              \         \           /  \       /
               \        [WARP_LAYER]    |     /
                \             |         |    /
                 -------[COST_VOLUME]   |   /
                  \           |        /   /
                   -------[LAYER 0]--------
                             ...
                         [LAYER N-1]
                              |
                         final_output
        :param features1: Tensor. Feature map of shape [batch_size, H, W, num_features]. Time = 0.
        :param features2: Tensor. Feature map of shape [batch_size, H, W, num_features]. Time = 1.
        :param optical_flow: Tensor or None. Optical flow of shape [batch_size, H, W, 2].
        :param previous_estimator_feature: Tensor or None. Feature map of shape [batch_size, H, W, num_features].
        :param pre_warp_scaling: Tensor or scalar. Scaling to be applied right before warping.
        :param reuse_variables: Tensorflow reuse option. i.e. tf.AUTO_REUSE.
        :return: final_flow: Tensor. Optical flow of shape [batch_size, H, W, 2].
                 layer_outputs: List of all convolution outputs of the network. The last item is the final_flow.
                 dense_outputs: List of dense outputs from the convolution tower. List is empty if network is not dense.
        """
        with tf.variable_scope(self.name, reuse=reuse_variables):
            # Warp layer.
            warped = features2
            if optical_flow is not None:
                warped = backward_warp(warped, optical_flow * pre_warp_scaling)

            # Cost volume layer.
            cv = cost_volume(features1, warped, search_range=self.search_range)
            if self.cost_volume_activation:
                cv = self.activation_fn(cv)

            # CNN layers.
            # Initial input has shape [batch_size, H, W, in_features + cv_size + 2]
            input_stack = [features1, cv]
            if optical_flow is not None:
                input_stack = input_stack + [optical_flow]
            if previous_estimator_feature is not None:
                input_stack = input_stack + [previous_estimator_feature]
            initial_input = tf.concat(input_stack, axis=-1, name='conv_tower_input')
            final_flow, layer_outputs, dense_outputs = self._get_conv_tower(initial_input)

            return final_flow, layer_outputs, dense_outputs
