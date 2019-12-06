from story.utils import result_replace
import numpy as np


class GPT2Generator:
    def __init__(self, **kwargs):
        pass

    def generate(self, prompt, debug_print=False):
        if debug_print:
            print("******DEBUG******")
            print("Prompt is: ", repr(prompt))

        for _ in range(5):
            text = "DUMMY_RESPONSE_" + str(np.random.randint(0, 999999))
            if debug_print:
                print("Generated result is: ", repr(text))
                print("******END DEBUG******")

            result = result_replace(text)
            if len(result) > 0:
                break
        return result
