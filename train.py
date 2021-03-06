from __future__ import print_function
from keras.callbacks import LambdaCallback
from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.layers import LSTM
import numpy as np
import random
import sys
import os
import io
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-data', default='training_data.txt',
                    help='''Dataset to use for training. Recommended size >500KB.
                    Default: "training_data.txt"''')
parser.add_argument('-weights', default='',
                    help='''If you want to resume from a trained weight, add the path to
                    the h5 weight here. The weights are automatically saved each epoch.''')
parser.add_argument('-randomness', type=float, default=0.05,
                    help='''The exponential factor determining the predicted character
                    to be chosen. Do not change unless you know what you're doing. Default: 0.05''')
parser.add_argument('-epochs', type=int, default=200,
                    help='''Number of epoches to do. I recommend >50 atleast. Default: 200''')
parser.add_argument('-batch_size', type=int, default=128,
                    help='''Batch size. If you get a OutOfMemory error, reduce the batch size.
                    On big memory GPUs, you can increase this, but not by much. Default: 128''')
parser.add_argument('-save_dir', default='weights',
                    help='''Directory where to save the weights. Default: weights''')
args = vars(parser.parse_args())

save_path = args['save_dir']
if not os.path.exists(save_path) or not os.path.isdir(save_path):
    os.makedirs(save_path)

path = args['data']
with io.open(path, encoding='utf-8') as f:
    text = f.read()
print('corpus length:', len(text))

chars = sorted(list(set(text)))
print('total chars:', len(chars))
char_indices = dict((c, i) for i, c in enumerate(chars))
indices_char = dict((i, c) for i, c in enumerate(chars))

# cut the text in semi-redundant sequences of maxlen characters
maxlen = 40
step = 3
sentences = []
next_chars = []
for i in range(0, len(text) - maxlen, step):
    sentences.append(text[i: i + maxlen])
    next_chars.append(text[i + maxlen])

print('Vectorization...')
x = np.zeros((len(sentences), maxlen, len(chars)), dtype=np.bool)
y = np.zeros((len(sentences), len(chars)), dtype=np.bool)
for i, sentence in enumerate(sentences):
    for t, char in enumerate(sentence):
        x[i, t, char_indices[char]] = 1
    y[i, char_indices[next_chars[i]]] = 1


# build the model: 2 LSTM
print('Build model...')
model = Sequential()
model.add(LSTM(128, input_shape=(maxlen, len(chars)), return_sequences=True))
model.add(LSTM(128))
model.add(Dense(len(chars)))
model.add(Activation('softmax'))
model.compile(loss='categorical_crossentropy', optimizer='rmsprop')


def on_epoch_end(epoch, logs):
    # Function invoked at end of each epoch. Prints generated text. Also saves model.
    model.save(os.path.join(save_path, "trained_model_weights_%d.h5" % (epoch,)))
    print("Saved model.")

    print()
    print('----- Generating text after Epoch: %d -----' % epoch)

    start_index = random.randint(0, len(text) - maxlen - 1)
    generated = ''
    sentence = text[start_index: start_index + maxlen]
    generated += sentence
    print('----- Generating with seed: "' + sentence.replace("\n", "\\n") + '" -----')
    print()
    sys.stdout.write(generated)

    for i in range(400):
        x_pred = np.zeros((1, maxlen, len(chars)))
        for t, char in enumerate(sentence):
            x_pred[0, t, char_indices[char]] = 1.

        preds = np.asarray(model.predict(x_pred, verbose=0)[0]).astype('float')
        preds = np.exp(np.log(preds*args['randomness']))
        preds /= np.sum(preds)
        preds = np.random.multinomial(1, preds, 1)
        next_index = np.argmax(preds)
        next_char = indices_char[next_index]

        generated += next_char
        sentence = sentence[1:] + next_char

        sys.stdout.write(next_char)
        sys.stdout.flush()
    print()


print_callback = LambdaCallback(on_epoch_end=on_epoch_end)
if args['weights'] != "":
    model.load_weights(args['weights'])
model.fit(x, y,
          batch_size=args['batch_size'],
          epochs=args['epochs'],
          callbacks=[print_callback])
