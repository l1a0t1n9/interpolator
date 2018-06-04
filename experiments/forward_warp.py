import tensorflow as tf
from utils.misc import print_tensor_shape


def forward_warp(features, flow, max_image_area=1280*720):
    """
    For an algorithm that gives the same end result, see section 3 in https://arxiv.org/pdf/1711.05890.pdf.
    Note that the actual implementation here is not n^2, and should be linear in GPU memory.
    :param features: A Tensor. Features to be warped, of shape [batch_size, H, W, C].
    :param flow: A Tensor. Un-normalized flow in image pixel units, of shape [batch_size, H, W, 2].
    :param max_image_area: The maximum value for width * height of the input features. It is ok to specify a value
                           larger than the actual area (at the expense of performance), but it cannot be any less.
    """

    # Flip (x, y) to (y, x) for flow, to avoid further confusion.
    flow = tf.reverse(flow, axis=[-1])

    # Get target indices along with corresponding values to add.
    indices, splat_values = get_translated_pixels(features, flow)

    # Mask out out-of-bounds splat values
    height, width, channels = tf.shape(features)[1], tf.shape(features)[2], tf.shape(features)[3]
    greater_than_zero = tf.greater_equal(indices, 0)
    greater_than_zero = tf.cast(tf.reduce_all(greater_than_zero, axis=-1), tf.float32)
    less_than_height = tf.cast(tf.less(indices[..., 0], height), tf.float32)
    less_than_width = tf.cast(tf.less(indices[..., 1], width), tf.float32)
    within_bounds = greater_than_zero * less_than_height * less_than_width
    splat_values *= tf.expand_dims(within_bounds, axis=-1)

    # Clip indices and flatten.
    y_indices = tf.clip_by_value(indices[..., 0], 0, height)
    x_indices = tf.clip_by_value(indices[..., 1], 0, width)
    flattened_indices = y_indices * width + x_indices

    # Partition and aggregate based on target index.
    def _aggregate_to_target(elems):
        vals, indices = elems
        partitions = tf.dynamic_partition(vals, indices, max_image_area)
        values = []
        for i in range(len(partitions)):
            value = tf.where(tf.size(partitions[i]) > 0,
                             x=tf.reduce_sum(partitions[i], axis=0),
                             y=tf.zeros(tf.shape(partitions[i])[1:]))
            values.append(value)
        values = tf.stack(values, axis=0)
        values = values[:height * width]
        values = tf.reshape(values, (height, width, channels))

        # map_fn requires us to return the same number of things as arguments (nested structure must match).
        # See: https://stackoverflow.com/questions/47984876/tensorflow-tf-map-fn-parameters
        return values, values

    # After this, values has shape [batch_size, height, width, 1].
    values, _ = tf.map_fn(_aggregate_to_target, (splat_values, flattened_indices), back_prop=True)

    # Scatter into output. A bunch of transposing to work around the batch dimension is involved.
    x_1d, y_1d = tf.range(0, width), tf.range(0, height)
    x_2d, y_2d = tf.meshgrid(x_1d, y_1d)
    indices_2d = tf.stack([y_2d, x_2d], axis=-1)
    ordered_indices = tf.reshape(indices_2d, (-1, 2))
    values = tf.transpose(values, [1, 2, 3, 0])
    transposed_features = tf.transpose(features, [1, 2, 3, 0])
    warped = tf.scatter_nd(ordered_indices, values, tf.shape(transposed_features))
    warped = tf.transpose(warped, [3, 0, 1, 2])
    return warped


def get_translated_pixels(features, translations):
    """
    :param features: A Tensor. Of shape [batch_size, H, W, C].
    :param translations: A Tensor. Translations in image pixel units, of shape [batch_size, H, W, 2].
    :return: indices: Tensor of shape [batch_size, num_indices, 2]. The indices to target.
             values: Tensor of shape [batch_size, num_indices, C]. The values to put at the corresponding indices.
    """

    # Get translated mesh-grid.
    fshape = tf.shape(features)
    batch_size, height, width, channels = fshape[0], fshape[1], fshape[2], fshape[3]
    x_1d, y_1d = tf.range(0, width), tf.range(0, height)
    x_2d, y_2d = tf.meshgrid(x_1d, y_1d)
    indices_2d = tf.cast(tf.stack([y_2d, x_2d], axis=-1), tf.float32)
    translated_indices = translations + indices_2d

    # Get splat corners.
    ceiled = tf.cast(tf.ceil(translated_indices), tf.int32)
    floored = tf.cast(tf.floor(translated_indices), tf.int32)
    tl_indices = floored
    tr_indices = tf.stack([floored[..., 0], ceiled[..., 1]], axis=-1)
    br_indices = ceiled
    bl_indices = tf.stack([ceiled[..., 0], floored[..., 1]], axis=-1)

    # Compute splat values, using inverse bi-linear interpolation formula.
    tl_diff = tf.expand_dims(tf.abs(tf.cast(tl_indices, tf.float32) - translated_indices), axis=-1)
    tr_diff = tf.expand_dims(tf.abs(tf.cast(tr_indices, tf.float32) - translated_indices), axis=-1)
    br_diff = tf.expand_dims(tf.abs(tf.cast(br_indices, tf.float32) - translated_indices), axis=-1)
    bl_diff = tf.expand_dims(tf.abs(tf.cast(bl_indices, tf.float32) - translated_indices), axis=-1)
    tl_vals = features * (1.0 - tl_diff[..., 0, :]) * (1.0 - tl_diff[..., 1, :])
    tr_vals = features * (1.0 - tr_diff[..., 0, :]) * (1.0 - tr_diff[..., 1, :])
    br_vals = features * (1.0 - br_diff[..., 0, :]) * (1.0 - br_diff[..., 1, :])
    bl_vals = features * (1.0 - bl_diff[..., 0, :]) * (1.0 - bl_diff[..., 1, :])

    # Zero out certain splat values if x and y have integer coordinates (ceil and floor are the same).
    # Otherwise we get incorrect duplication.
    ceiled_compare = tf.cast(ceiled, tf.float32)
    not_duplicated = 1.0 - tf.cast(tf.equal(ceiled_compare, translated_indices), tf.float32)
    tr_vals *= tf.expand_dims(not_duplicated[..., 1], axis=-1)
    br_vals *= tf.expand_dims(not_duplicated[..., 0], axis=-1)
    bl_vals *= tf.expand_dims(not_duplicated[..., 0] * not_duplicated[..., 1], axis=-1)

    # Combine and flatten shape.
    all_indices = tf.stack([tl_indices, tr_indices, br_indices, bl_indices], axis=0)
    all_vals = tf.stack([tl_vals, tr_vals, br_vals, bl_vals], axis=0)
    all_indices = tf.reshape(all_indices, (batch_size, -1, 2))
    all_vals = tf.reshape(all_vals, (batch_size, -1, channels))
    return all_indices, all_vals