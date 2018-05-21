import tensorflow as tf


class Trainer:
    def __init__(self, model, dataset, session, config, verbose=True):
        """
        :param model: A neural network model.
        :param dataset: A dataset object.
        :param session: Tensorflow session.
        :param config: Dictionary.
        :param verbose: Bool.
        """
        assert isinstance(session, tf.Session)
        self.model = model
        self.dataset = dataset
        self.session = session
        self.config = config
        self.verbose = verbose

    def train(self, validate_every=100):
        """
        Runs an infinite training loop that validates every so often.
        :param validate_every: Perform validation at this interval.
        :return: Nothing.
        """
        while True:
            self.train_for(validate_every)
            if self.verbose:
                print('Validating.')
            self.validate(self.config['validation_iterations'])

    def train_for(self, iterations):
        """
        :param iterations: Number of iterations to train for.
        :return: Nothing.
        """
        raise NotImplementedError('train_for() is not implemented.')

    def validate(self, iterations):
        raise NotImplementedError('validate() is not implemented.')
