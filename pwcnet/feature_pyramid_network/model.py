import tensorflow as tf
from common.models import ConvNetwork
from common.utils.tf import leaky_relu


class FeaturePyramidNetwork(ConvNetwork):
    def __init__(self, name='feature_pyramid_network', layer_specs=None,
                 activation_fn=leaky_relu,
                 regularizer=None, dense_net=False):
        """
        :param name: Str. For variable scoping.
        :param layer_specs: See parent class.
        :param activation_fn: Tensorflow activation function.
        :param regularizer: Tf regularizer such as tf.contrib.layers.l2_regularizer.
        :param dense_net: Bool.
        """
        if layer_specs is None:
            # PWC-Net default.
            layer_specs = [[3, 16, 1, 2],
                           [3, 16, 1, 1],
                           [3, 16, 1, 1],  # C1
                           [3, 32, 1, 2],
                           [3, 32, 1, 1],
                           [3, 32, 1, 1],  # C2
                           [3, 64, 1, 2],
                           [3, 64, 1, 1],
                           [3, 64, 1, 1],  # C3
                           [3, 96, 1, 2],
                           [3, 96, 1, 1],
                           [3, 96, 1, 1],  # C4
                           [3, 128, 1, 2],
                           [3, 128, 1, 1],
                           [3, 128, 1, 1],  # C5
                           [3, 192, 1, 2],
                           [3, 192, 1, 1],
                           [3, 192, 1, 1]]  # C6

        super().__init__(name=name, layer_specs=layer_specs,
                         activation_fn=activation_fn, regularizer=regularizer, padding='SAME', dense_net=dense_net)

    def get_forward(self, image, reuse_variables=tf.AUTO_REUSE):
        """
           input
             |
         [LAYER 0]
            ...
        [LAYER N-1]
             |
        final_features
        :param image: Tensor. Shape [batch_size, H, W, 3].
        :param reuse_variables: tf reuse option. i.e. tf.AUTO_REUSE.
        :return: final_features: features of shape [batch_size, H, W, 192].
                 layer_outputs: array of layer intermediate conv outputs. Length is len(layer_specs) + 1.
        """
        with tf.variable_scope(self.name, reuse=reuse_variables):
            final_features, layer_outputs, _ = self._get_conv_tower(image)
            return final_features, layer_outputs

    def get_c_n_idx(self, n):
        """
        As notated in the PWC-Net paper, returns feature map c^n.
        :param n: Int. Typically between 1 to 6.
        :return: Int. Index of the layer_outputs array.
        """
        return n * 3 - 1
