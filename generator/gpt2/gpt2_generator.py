from story.utils import *
import warnings

warnings.filterwarnings("ignore")
import os
import tensorflow as tf

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
from generator.gpt2.src import sample, encoder, model
import json


class GPT2Generator:

    def __init__(self, generate_num=120, temperature=0.4, top_k=40, top_p=0.9):
        self.generate_num = generate_num
        self.temp = temperature
        self.top_k = top_k
        self.top_p = top_p

        self.model_name = "model_v5"
        self.model_dir = "generator/gpt2/models"
        self.checkpoint_path = os.path.join(self.model_dir, self.model_name)

        models_dir = os.path.expanduser(os.path.expandvars(self.model_dir))
        self.batch_size = 1
        self.samples = 1

        self.enc = encoder.get_encoder(self.model_name, models_dir)
        hparams = model.default_hparams()
        with open(os.path.join(models_dir, self.model_name, 'hparams.json')) as f:
            hparams.override_from_dict(json.load(f))

        config = tf.compat.v1.ConfigProto()
        config.gpu_options.allow_growth = True
        self.sess = tf.compat.v1.Session(config=config)

        self.context = tf.placeholder(tf.int32, [self.batch_size, None])
        # np.random.seed(seed)
        # tf.set_random_seed(seed)
        self.output = sample.sample_sequence(
            hparams=hparams, length=self.generate_num,
            context=self.context,
            batch_size=self.batch_size,
            temperature=temperature, top_k=top_k, top_p=top_p
        )
        self.top_output = sample.sample_sequence(
            hparams=hparams, length=self.generate_num,
            context=self.context,
            batch_size=self.batch_size,
            temperature=0
        )

        saver = tf.train.Saver()
        ckpt = tf.train.latest_checkpoint(os.path.join(models_dir, self.model_name))
        saver.restore(self.sess, ckpt)

    def generate_raw(self, prompt, use_top: bool):
        context_tokens = self.enc.encode(prompt)
        out = self.sess.run(self.top_output if use_top else self.output, feed_dict={
            self.context: [context_tokens]
        })[0, len(context_tokens):]
        return self.enc.decode(out)

    def generate(self, prompt, debug_print=False, use_top=False):

        if debug_print:
            print("******DEBUG******")
            print("Prompt is: ", repr(prompt))

        for _ in range(5):
            text = self.generate_raw(prompt, use_top)
            if debug_print:
                print("Generated result is: ", repr(text))
                print("******END DEBUG******")

            result = result_replace(text)
            if len(result) > 0:
                break
        return result
