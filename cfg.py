"""
    Code for building language models from (P)CFGs
"""
from __future__ import division

import random
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable
from sklearn.utils import shuffle
from nltk.parse.generate import generate
from nltk import CFG, PCFG

m = __import__("model-bare")

# Language parameters
DEPTH = 5
MIN_LENGTH = 2
STD_LENGTH = 2
MAX_LENGTH = 2 ** (DEPTH - 1)
MEAN_LENGTH = MAX_LENGTH / 2

# Hyperparameters
LEARNING_RATE = .01  # .01 and .1 seem to work well?
BATCH_SIZE = 10  # 10 is the best I've found
READ_SIZE = 2  # length of vectors on the stack

CUDA = False
EPOCHS = 30

grammar = PCFG.fromstring("""S -> S S [0.2]
 S -> '(' S ')' [0.2] | '(' ')' [0.2]
 S -> '[' S ']' [0.2] | '[' ']' [0.2]""")

# print grammar

parenthesis_strings = list(generate(grammar, depth=5))

model = m.FFController(3, READ_SIZE, 3)
if CUDA:
    model.cuda()

criterion = nn.CrossEntropyLoss()

code_for = {u'(': 0, u')': 1, u'[': 2, u']': 3, '#': 4}


def randstr():
    #	return [random.randint(0, 1) for _ in xrange(length)]
    string = random.choice(parenthesis_strings)
    return [code_for[s] for s in string]


reverse = lambda s: s[::-1]
onehot = lambda b: torch.FloatTensor([1. if i == b else 0. for i in xrange(len(code_for))])


def get_tensors(B):
    X_raw = [randstr() for _ in xrange(B)]

    # initialize X to one-hot encodings of NULL
    X = torch.FloatTensor(B, MAX_LENGTH, len(code_for))
    X[:, :, :len(code_for) - 1].fill_(0)
    X[:, :, len(code_for) - 1].fill_(1)

    # initialize Y to NULL
    Y = torch.LongTensor(B)
    Y.fill_(0)

    for i, x in enumerate(X_raw):
        length = min(max(MIN_LENGTH - 1, int(random.gauss(MEAN_LENGTH, STD_LENGTH))), len(x) - 1)
        for j, char in enumerate(x[:length]):
            X[i, j, :] = onehot(char)
        Y[i] = x[length]
    return Variable(X), Variable(Y)


train_X, train_Y = get_tensors(800)

# print train_X[0,0,:]
# print train_Y[0]

dev_X, dev_Y = get_tensors(100)
test_X, test_Y = get_tensors(100)


def train(train_X, train_Y):
    model.train()
    total_loss = 0.

    for batch, i in enumerate(xrange(0, len(train_X.data) - BATCH_SIZE, BATCH_SIZE)):

        digits_correct = 0
        digits_total = 0
        batch_loss = 0.

        X, Y = train_X[i:i + BATCH_SIZE, :, :], train_Y[i:i + BATCH_SIZE]
        model.init_stack(BATCH_SIZE)
        valid_X = (X[:, :, len(code_for) - 1] != 1)
        lengths_X = torch.sum(valid_X, 1)

        A = Variable(torch.FloatTensor(B, len(code_for)))

        for j in xrange(MAX_LENGTH):
            a = model.forward(X[:, j, :])
            A[:, j] = torch.transpose(a, 0, 1)

            ##############  to here !!!!!!!!!!!!!!!!!
            batch_loss += criterion(valid_a, valid_Y)

        # update the weights
        optimizer.zero_grad()
        batch_loss.backward()
        optimizer.step()

        total_loss += batch_loss.data
        if batch % 10 == 0:
            print "batch {}: loss={:.4f}, acc={:.2f}".format(batch, sum(batch_loss.data) / BATCH_SIZE,
                                                             digits_correct / digits_total)


def evaluate(test_X, test_Y):
    model.eval()
    total_loss = 0.
    digits_correct = 0
    digits_total = 0
    model.init_stack(len(test_X.data))
    for j in xrange(2 * MAX_LENGTH):

        a = model.forward(test_X[:, j, :])

        # print the (first) stack after every step
        model.stack.log0()

        indices = test_Y[:, j] != 2
        valid_a = a[indices.view(-1, 1)].view(-1, 3)
        valid_Y = test_Y[:, j][indices]

        if len(valid_a) == 0: continue

        _, valid_y_ = torch.max(valid_a, 1)
        digits_total += len(valid_a)
        digits_correct += len(torch.nonzero((valid_y_ == valid_Y).data))
        total_loss += criterion(valid_a, valid_Y)

    print model.state_dict()
    print "epoch {}: loss={:.4f}, acc={:.2f}".format(epoch, sum(total_loss.data) / len(test_X),
                                                     digits_correct / digits_total)


# optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)
optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
print "hyperparameters: lr={}, batch_size={}, read_dim={}".format(LEARNING_RATE, BATCH_SIZE, READ_SIZE)
for epoch in xrange(EPOCHS):
    print "-- starting epoch {} --".format(epoch)
    perm = torch.randperm(800)
    train_X, train_Y = train_X[perm], train_Y[perm]
    train(train_X, train_Y)
    evaluate(dev_X, dev_Y)
