import tensorflow as tf
import optparse
from context_interp.vgg19.vgg19 import Vgg19
import os
import inspect

cur_dir = os.path.dirname(os.path.realpath(__file__))

# This does not work nicely with our modules, would need to move this script to root folder.
# parser = optparse.OptionParser()
# parser.add_option('-d', '--data-path',
#     action="store", dest="data_path",
#     help="Full path to the full vgg19 npy file to process.", default="")
#
# parser.add_option('-o', '--output-path',
#     action="store", dest="output_path",
#     help="Full path to directory in which the partial vgg19 npy file, up to conv4_4, will be output.",
#     default=cur_dir)
#
# options, args = parser.parse_args()
#
# if args.data_path == "":
#     parser.error('--data-path argument must be provided.')

data_path = cur_dir + '/vgg19.npy'
output_path = cur_dir + '/vgg19_conv4_4.npy'
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
sess = tf.Session(config=config)

# Load completely.
vgg19 = Vgg19(vgg19_npy_path=data_path)
image_input = tf.placeholder(shape=[None, 224, 224, 3], dtype=tf.float32)
vgg19.build_up_to_conv4_4(image_input)
sess.run(tf.global_variables_initializer())

# Save partially.
vgg19.save_npy(sess, npy_path=output_path)
