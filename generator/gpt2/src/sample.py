import tensorflow as tf
import math
from generator.gpt2.src import model


def penalize_used(logits, output, penalty: float):
    # output has shape (1, len) and type int32 - ASSUMES batchsize 1
    # NEED TO penalize all output because the model likes to repeat the input
    output = output[0]
    n_vocab = logits.shape[1]
    # N = tf.shape(output)[0]  # lookback
    # N_float = tf.cast(N, dtype=tf.float32)
    # weights = tf.range(1, N_float + 1, dtype=tf.float32) / N_float  # Invariant: previous token is weight 1
    # counts = tf.math.bincount(output, weights=weights,
    #                           minlength=n_vocab)
    # counts = tf.expand_dims(counts, 0)
    # return tf.compat.v1.where(tf.cast(counts, dtype=tf.bool), logits * .85, logits)
    # return logits + counts * math.log(.6)  # A token is p times as likely to be repeated consecutively

    y, _ = tf.unique(output[::-1])  # y is the unique tokens, starting from most recent
    len_y = tf.cast(tf.shape(y)[0], dtype=tf.float32)
    # Invariant: previous token is weight 1
    weights = tf.range(len_y * 3 + 1, len_y + 1, delta=-2, dtype=tf.float32) * (penalty / len_y / 3)
    penalties = tf.scatter_nd(tf.expand_dims(y, 1), weights, [n_vocab])
    return logits * tf.expand_dims(1 - penalties, 0)


def top_k_logits(logits, k):
    def _top_k():
        values, _ = tf.nn.top_k(logits, k=k)
        min_values = values[:, -1, tf.newaxis]
        return tf.where(
            logits < min_values,
            tf.ones_like(logits, dtype=logits.dtype) * -1e10,
            logits,
        )

    return tf.cond(
        tf.equal(k, 0),
        lambda: logits,
        lambda: _top_k(),
    )


def top_p_logits(logits, p):
    """Nucleus sampling"""
    if p >= 1:
        return logits
    batch, _ = logits.shape.as_list()
    sorted_logits = tf.sort(logits, direction='DESCENDING', axis=-1)
    cumulative_probs = tf.cumsum(tf.nn.softmax(sorted_logits, axis=-1), axis=-1)
    indices = tf.stack([
        tf.range(0, batch),
        # number of indices to include
        tf.maximum(tf.reduce_sum(tf.cast(cumulative_probs <= p, tf.int32), axis=-1) - 1, 0),
    ], axis=-1)
    min_values = tf.gather_nd(sorted_logits, indices)
    return tf.where(
        logits < min_values,
        tf.ones_like(logits) * -1e10,
        logits,
    )


def sample_sequence(hparams, length, start_token=None, batch_size=None, context=None,
                    temperature=1, top_k=None, top_p=None, penalty=0):
    if start_token is None:
        assert context is not None, 'Specify exactly one of start_token and context!'
    else:
        assert context is None, 'Specify exactly one of start_token and context!'
        context = tf.fill([batch_size, 1], start_token)

    def step(hparams, tokens, past=None):
        lm_output = model.model(hparams=hparams, X=tokens, past=past, reuse=tf.AUTO_REUSE)

        logits = lm_output['logits'][:, :, :hparams.n_vocab]
        presents = lm_output['present']
        presents.set_shape(model.past_shape(hparams=hparams, batch_size=batch_size))
        return {
            'logits': logits,
            'presents': presents,
        }

    with tf.name_scope('sample_sequence'):
        def body(past, prev, output):
            next_outputs = step(hparams, prev, past=past)
            logits = next_outputs['logits'][:, -1, :]
            if temperature == 0:
                samples = tf.expand_dims(tf.argmax(logits, axis=-1, output_type=tf.int32), axis=-1)
            else:
                logits = logits / tf.to_float(temperature)
                if penalty > 0:
                    logits = penalize_used(logits, output, penalty)
                if top_k is not None:
                    logits = top_k_logits(logits, k=top_k)
                if top_p is not None:
                    logits = top_p_logits(logits, p=top_p)
                samples = tf.random.categorical(logits, num_samples=1, dtype=tf.int32)
            return [
                next_outputs['presents'] if past is None else tf.concat([past, next_outputs['presents']], axis=-2),
                samples,
                tf.concat([output, samples], axis=1)
            ]

        past, prev, output = body(None, context, context)

        def cond(*args):
            return True

        _, _, tokens = tf.while_loop(
            cond=cond, body=body,
            maximum_iterations=length - 1,
            loop_vars=[
                past,
                prev,
                output
            ],
            shape_invariants=[
                tf.TensorShape(model.past_shape(hparams=hparams, batch_size=batch_size)),
                tf.TensorShape([batch_size, None]),
                tf.TensorShape([batch_size, None]),
            ],
            back_prop=False,
        )

        return tokens
