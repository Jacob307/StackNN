"""
Word prediction tasks based on CFGs. In each task in this module, the
neural network will read a sentence (sequence of words) and predict the
next word. We may specify a list of words that must be predicted by the
neural network. For example, if we specify that the controller must predict
verbs, then we only evaluate it based on the predictions made when the
correct answer is a verb.

Tasks are distinguished from one another based on how input and output
data are generated for training and testing. In all tasks below, the
data are generated by some sort of context-free grammar.
"""
# TODO: Make another version of CFGTask for PCFGs
from __future__ import division

import random
from abc import ABCMeta

import nltk.grammar as gr
import torch
import torch.nn as nn
from nltk.parse.generate import generate
from torch.autograd import Variable

from models import VanillaModel
from controllers.feedforward import LinearSimpleStructController
from structs import Stack
from tasks.language_modeling import LanguageModelingTask


class CFGTask(LanguageModelingTask):
    """
    In this task, the input and output data used for training and
    evaluation are based on examples uniformly sampled from a set of
    sentences generated by a deterministic context-free grammar.
    """


    class Params(LanguageModelingTask.Params):

        def __init__(self, grammar, to_predict, sample_depth, **kwargs):
            self.grammar = grammar
            self.sample_depth = sample_depth
            self.train_set_size = kwargs.get("train_set_size", 800)
            self.test_set_size = kwargs.get("test_set_size", 100)
            super(CFGTask.Params, self).__init__(to_predict, **kwargs)


    def __init__(self, params):
        super(CFGTask, self).__init__(params)
        print "Sample depth: %d" % self.sample_depth
        print "Max length: %d" % self.max_length

        self.sample_strings = self.generate_sample_strings()
        print "{} strings generated".format(len(self.sample_strings))
        if len(self.sample_strings) > 0:
            max_sample_length = max([len(x) for x in self.sample_strings])
        else:
            max_sample_length = 0
        print "Maximum sample length: " + str(max_sample_length)
        print "Maximum input length: " + str(self.max_x_length)

    @property
    def input_size(self):
        return self.alphabet_size

    @property
    def output_size(self):
        return self.alphabet_size

    def _init_alphabet(self, null):
        """
        Creates an encoding of a CFG's terminal symbols as numbers.

        :type null: unicode
        :param null: A string representing "null"

        :rtype: dict
        :return: A dict associating each terminal of the grammar with a
            unique number. The highest number represents "null"
        """
        rhss = [r.rhs() for r in self.grammar.productions()]
        rhs_symbols = set()
        rhs_symbols.update(*rhss)
        rhs_symbols = set(x for x in rhs_symbols if gr.is_terminal(x))

        alphabet = {x: i for i, x in enumerate(rhs_symbols)}
        alphabet[null] = len(alphabet)

        return alphabet

    """ Data Generation """

    def get_data(self):
        """
        Generates training and testing datasets for this task using the
        self.get_tensors method.

        :return: None
        """
        self.train_x, self.train_y = self.get_tensors(self.train_set_size)
        self.test_x, self.test_y = self.get_tensors(self.test_set_size)

    def generate_sample_strings(self, remove_duplicates=True):
        """
        Generates all strings from self.grammar up to the depth
        specified by self.depth. Duplicates may optionally be removed.

        :type remove_duplicates: bool
        :param remove_duplicates: If True, duplicates will be removed

        :rtype: list
        :return: A list of strings generated by self.grammar
        """
        generator = generate(self.grammar, depth=self.sample_depth)
        if remove_duplicates:
            return [list(y) for y in set(tuple(x) for x in generator)]
        else:
            return list(generator)

    def get_tensors(self, num_tensors):
        """
        Generates a dataset for this task. Each input consists of a
        sentence generated by self.grammar. Each output consists of a
        list of words such that the jth word is the correct prediction
        the neural network should make after having read the jth input
        word. In this case, the correct prediction is the next word.

        Input words are represented in one-hot encoding. Output words
        are represented numerically according to self.code_for. Each
        sentence is truncated to a fixed length of self.max_length. If
        the sentence is shorter than this length, then it is padded with
        "null" symbols. The dataset is represented as two tensors, x and
        y; see self._evaluate_step for the structures of these tensors.

        :type num_tensors: int
        :param num_tensors: The number of sentences to include in the
            dataset

        :rtype: tuple
        :return: A Variable containing the input dataset and a Variable
            containing the output dataset
        """
        x_raw = [self.get_random_sample_string() for _ in xrange(num_tensors)]
        y_raw = [s[1:] for s in x_raw]

        x_var = self.sentences_to_one_hot(self.max_x_length, *x_raw)
        y_var = self.sentences_to_codes(self.max_y_length, *y_raw)

        return x_var, y_var

    def get_random_sample_string(self):
        """
        Randomly chooses a sentence from self.sample_strings with a
        uniform distribution.

        :rtype: list
        :return: A sentence from self.sample_strings
        """
        return random.choice(self.sample_strings)

    """ Data Visualization """

    @property
    def generic_example(self):
        """
        The string for visualizations.

        TODO: Make this a function of the grammar.
        """
        return [u"#"]


class CFGTransduceTask(CFGTask):
    """
    This task is like CFGTask, except that the controller receives symbols
    with even indices as input, and must predict the symbols with odd
    indices.
    """

    def get_tensors(self, num_tensors):
        """
        Generates a dataset for this task. Each input consists of a
        sentence generated by self.grammar. Each output consists of a
        list of words such that the jth word is the correct prediction
        the neural network should make after having read the jth input
        word. In this case, the correct prediction is the next word.

        Input words are represented in one-hot encoding. Output words
        are represented numerically according to self.code_for. Each
        sentence is truncated to a fixed length of self.max_length. If
        the sentence is shorter than this length, then it is padded with
        "null" symbols. The dataset is represented as two tensors, x and
        y; see self._evaluate_step for the structures of these tensors.

        :type num_tensors: int
        :param num_tensors: The number of sentences to include in the
            dataset

        :rtype: tuple
        :return: A Variable containing the input dataset and a Variable
            containing the output dataset
        """
        x_orig = [self.get_random_sample_string() for _ in xrange(num_tensors)]
        x_raw = [a[::2] for a in x_orig]
        y_raw = [a[1::2] for a in x_orig]

        x_var = self.sentences_to_one_hot(self.max_x_length, *x_raw)
        y_var = self.sentences_to_codes(self.max_y_length, *y_raw)

        return x_var, y_var
