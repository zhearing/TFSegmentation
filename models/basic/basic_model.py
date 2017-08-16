"""
This file will contain the basic model of the segmentation problem
Any segmentation model will inherit from it .
You can override any function you want
"""

from utils.img_utils import decode_labels

import tensorflow as tf


class Params:
    """
    Class to hold BasicModel parameters
    """

    def __init__(self):
        self.img_width = None
        self.img_height = None
        self.num_channels = None
        self.num_classes = None


class BasicModel:
    """
    Base class for any segmentation model
    """

    def __init__(self, args):
        self.args = args
        self.params = Params()
        # Init parameters
        self.params.img_width = self.args.img_width
        self.params.img_height = self.args.img_height
        self.params.num_channels = self.args.num_channels
        self.params.num_classes = self.args.num_classes
        # Input
        self.x_pl = None
        self.y_pl = None
        self.is_training = None
        # Output
        self.logits = None
        self.out_softmax = None
        self.out_argmax = None
        self.out_one_hot = None
        self.y_argmax = None
        # Train
        self.cross_entropy_loss = None
        self.regularization_loss = None
        self.loss = None
        self.optimizer = None
        self.train_op = None
        # Summaries
        self.accuracy = None
        self.segmented_summary = None
        self.merged_summaries = None
        # Init global step
        self.global_step_tensor = None
        self.global_step_input = None
        self.global_step_assign_op = None
        self.init_global_step()
        # Init global epoch
        self.global_epoch_tensor = None
        self.global_epoch_input = None
        self.global_epoch_assign_op = None
        self.init_global_epoch()
        #########################################

    def init_global_epoch(self):
        """
        Create a global epoch tensor to totally save the process of the training
        :return:
        """
        with tf.variable_scope('global_epoch'):
            self.global_epoch_tensor = tf.Variable(0, trainable=False, name='global_epoch')
            self.global_epoch_input = tf.placeholder('int32', None, name='global_epoch_input')
            self.global_epoch_assign_op = self.global_epoch_tensor.assign(self.global_epoch_input)

    def init_global_step(self):
        """
        Create a global step variable to be a reference to the number of iterations
        :return:
        """
        with tf.variable_scope('global_step'):
            self.global_step_tensor = tf.Variable(0, trainable=False, name='global_step')
            self.global_step_input = tf.placeholder('int32', None, name='global_step_input')
            self.global_step_assign_op = self.global_step_tensor.assign(self.global_step_input)

    def build(self):
        """
        Override it in model class
        It will contain the logic of building a model
        :return:
        """
        raise NotImplementedError("build function is not implemented in the model")

    def init_input(self):
        with tf.name_scope('input'):
            self.x_pl = tf.placeholder(tf.float32, [None, self.params.img_height, self.params.img_width, 3])
            self.y_pl = tf.placeholder(tf.int32, [None, self.params.img_height, self.params.img_width])
            self.is_training = tf.placeholder(tf.bool)

    def init_network(self):
        raise NotImplementedError("init_network function is not implemented in the model")

    def init_output(self):
        with tf.name_scope('output'):
            self.out_softmax = tf.nn.softmax(self.logits)
            self.out_argmax = tf.argmax(self.out_softmax, axis=3)

    def init_train(self):
        with tf.name_scope('train-loss'):
            self.cross_entropy_loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=self.logits, labels=self.y_pl))
            self.regularization_loss = tf.reduce_sum(tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES))
            self.loss = self.cross_entropy_loss + self.regularization_loss

        with tf.name_scope('train-operation'):
            extra_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(extra_update_ops):
                self.optimizer = tf.train.AdamOptimizer(self.args.learning_rate)
                self.train_op = self.optimizer.minimize(self.loss)

    def init_summaries(self):
        with tf.name_scope('train-accuracy'):
            self.accuracy = tf.reduce_mean(tf.cast(tf.equal(self.y_pl, self.out_argmax), tf.float32))

        with tf.name_scope('segmented_output'):
            input_summary = tf.cast(self.x_pl, tf.uint8)
            labels_summary = tf.py_func(decode_labels, [self.y_pl, self.params.num_classes], tf.uint8)
            preds_summary = tf.py_func(decode_labels, [self.out_argmax, self.params.num_classes], tf.uint8)
            self.segmented_summary = tf.concat(axis=2, values=[input_summary, labels_summary, preds_summary])  # Concatenate row-wise

        # Every step evaluate these summaries
        with tf.name_scope('train-summary'):
            tf.summary.scalar('loss', self.loss)
            tf.summary.scalar('pixel_wise_accuracy', self.accuracy)

        self.merged_summaries = tf.summary.merge_all()