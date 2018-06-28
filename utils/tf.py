import tensorflow as tf
from tensorflow.python.ops import control_flow_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops import state_ops
from tensorflow.python.framework import ops
from tensorflow.python.training import optimizer


def print_tensor_shape(x):
    print(x.get_shape().as_list())


def tf_coin_flip(heads_rate):
    rand_val = tf.random_uniform([1], minval=0.0, maxval=1.0)
    is_head = tf.less(rand_val, heads_rate)
    return is_head


# https://github.com/tensorflow/tensorflow/issues/7712
def pelu(x):
    """Parametric Exponential Linear Unit (https://arxiv.org/abs/1605.09332v1)."""
    with tf.variable_scope(x.op.name + '_activation', initializer=tf.constant_initializer(1.0)):
        shape = x.get_shape().as_list()[1:]
        alpha = tf.get_variable('alpha', shape)
        beta = tf.get_variable('beta', shape)
        positive = tf.nn.relu(x) * alpha / (beta + 1e-9)
        negative = alpha * (tf.exp((-tf.nn.relu(-x)) / (beta + 1e-9)) - 1)
        return negative + positive


# https://stackoverflow.com/questions/39975676/how-to-implement-prelu-activation-in-tensorflow
def prelu(_x):
    with tf.variable_scope(_x.op.name + '_activation', initializer=tf.constant_initializer(1.0)):
        alphas = tf.get_variable('alpha', _x.get_shape()[-1],
                           initializer=tf.constant_initializer(0.0),
                            dtype=tf.float32)
        pos = tf.nn.relu(_x)
        neg = alphas * (_x - abs(_x)) * 0.5

        return pos + neg


def sliding_window_slice(x, slice_locations):
    """
    :param x: The tensor to window slice.
    :param slice_locations: A list. The locations at which we gather values. Values are either 0 or 1.
                            E.g [1, 0, 1] means that at each window offset j, we form [x[j], x[j + 2]].
    :return: The window sliced tensor. Is 1 rank higher than x.
    """
    slice_indices = []
    for i in range(len(slice_locations)):
        if slice_locations[i] == 1:
            slice_indices.append(i)

    sequence_len = len(slice_indices)

    # Get the sliding window indices.
    slice_indices_tensor = tf.constant(slice_indices)
    num_offsets = tf.shape(x)[0] - tf.cast(len(slice_locations) - 1, tf.int32)

    def get_zeros(sequence_len, x):
        return tf.zeros(tf.concat([[1, sequence_len], tf.shape(x)[1:]], axis=0))

    def get_slice(slice_indices_tensor, num_offsets, x):
        num_offsets = tf.maximum(num_offsets, 0)

        # Compute the gather indices for forming sequences.
        tiled = tf.tile(slice_indices_tensor, [num_offsets])
        tiled = tf.expand_dims(tiled, axis=0)
        tiled = tf.reshape(tiled, [num_offsets, -1])
        offsets = tf.expand_dims(tf.range(0, num_offsets), axis=1)
        indices = tiled + offsets
        indices = tf.reshape(indices, [-1])

        # Gather and reshape.
        images = tf.gather(x, indices)
        images = tf.expand_dims(images, axis=0)
        final_shape = tf.concat([[num_offsets, sequence_len], tf.shape(images)[2:]], axis=0)
        images = tf.reshape(images, final_shape)
        return tf.cast(images, tf.float32)

    slices = tf.cond(
        num_offsets > 0,
        true_fn=lambda: get_slice(slice_indices_tensor, num_offsets, x),
        false_fn=lambda: get_zeros(sequence_len, x)
    )
    return slices


# Copied from https://github.com/openai/iaf/blob/master/tf_utils/adamax.py.
# Commit 1f09a1b092d7bd406aededc5d5fc64fce766c55e.
class AdamaxOptimizer(optimizer.Optimizer):
    """Optimizer that implements the Adamax algorithm.
    See [Kingma et. al., 2014](http://arxiv.org/abs/1412.6980)
    ([pdf](http://arxiv.org/pdf/1412.6980.pdf)).
    @@__init__
    """

    def __init__(self, learning_rate=0.001, beta1=0.9, beta2=0.999, use_locking=False, name="Adamax"):
        super(AdamaxOptimizer, self).__init__(use_locking, name)
        self._lr = learning_rate
        self._beta1 = beta1
        self._beta2 = beta2

        # Tensor versions of the constructor arguments, created in _prepare().
        self._lr_t = None
        self._beta1_t = None
        self._beta2_t = None

    def _prepare(self):
        self._lr_t = ops.convert_to_tensor(self._lr, name="learning_rate")
        self._beta1_t = ops.convert_to_tensor(self._beta1, name="beta1")
        self._beta2_t = ops.convert_to_tensor(self._beta2, name="beta2")

    def _create_slots(self, var_list):
        # Create slots for the first and second moments.
        for v in var_list:
            self._zeros_slot(v, "m", self._name)
            self._zeros_slot(v, "v", self._name)

    def _apply_dense(self, grad, var):
        lr_t = math_ops.cast(self._lr_t, var.dtype.base_dtype)
        beta1_t = math_ops.cast(self._beta1_t, var.dtype.base_dtype)
        beta2_t = math_ops.cast(self._beta2_t, var.dtype.base_dtype)
        if var.dtype.base_dtype == tf.float16:
            eps = 1e-7  # Can't use 1e-8 due to underflow -- not sure if it makes a big difference.
        else:
            eps = 1e-8

        v = self.get_slot(var, "v")
        v_t = v.assign(beta1_t * v + (1. - beta1_t) * grad)
        m = self.get_slot(var, "m")
        m_t = m.assign(tf.maximum(beta2_t * m + eps, tf.abs(grad)))
        g_t = v_t / m_t

        var_update = state_ops.assign_sub(var, lr_t * g_t)
        return control_flow_ops.group(*[var_update, m_t, v_t])

    def _apply_sparse(self, grad, var):
        raise NotImplementedError("Sparse gradient updates are not supported.")