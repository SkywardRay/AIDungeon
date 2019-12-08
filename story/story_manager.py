import itertools

from story.utils import *
# from other.cacher import Cacher
import json
import uuid
from subprocess import Popen
import subprocess
import os
from generator.gpt2.gpt2_generator import GPT2Generator


class Story:

    def __init__(self, first_result, context="", seed=None, game_state=None, upload_story=False):
        self.story_start = context + first_result
        """the first generated text with context as prompt"""
        self.context = context
        """the initial non-generated part (part of story_start)"""
        self.rating = -1
        self.upload_story = upload_story

        self.actions = [""]
        "list of actions. First action is the prompt length should always equal that of story blocks"

        self.results = [first_result]
        "list of story blocks first story block follows prompt and is intro story"

        # Only needed in constrained/cached version
        self.seed = seed
        self.choices = []
        self.possible_action_results = None
        self.uuid = None

        if game_state is None:
            game_state = dict()
        self.game_state = game_state
        self.memory = 20
        """keep this many action-result pairs as context"""

    def __del__(self):
        self.save_to_storage()
        console_print("Game saved.")
        console_print("To load the game, type 'load' and enter the following ID: " + self.uuid)

    def init_from_dict(self, story_dict):
        self.story_start = story_dict["story_start"]
        self.seed = story_dict["seed"]
        self.actions = story_dict["actions"]
        self.results = story_dict["results"]
        self.choices = story_dict["choices"]
        self.possible_action_results = story_dict["possible_action_results"]
        self.game_state = story_dict["game_state"]
        self.context = story_dict["context"]
        self.uuid = story_dict["uuid"]

        if "rating" in story_dict.keys():
            self.rating = story_dict["rating"]
        else:
            self.rating = -1

    def initialize_from_json(self, json_string):
        story_dict = json.loads(json_string)
        self.init_from_dict(story_dict)

    def add_to_story(self, action, story_block):
        self.actions.append(action)
        self.results.append(story_block)

    def latest_result(self, num_history=None):
        if num_history is None:
            num_history = self.memory
        mem_texts = itertools.chain.from_iterable(zip(self.actions[-num_history + 1:], self.results[-num_history:]))
        # result = self.context if len(self.results) > num_history else self.story_start
        result = "\n".join((self.context, *mem_texts))
        return result

    def __str__(self):
        return self.latest_result(num_history=99999999)
        # story_list = [self.story_start]
        # for i in range(len(self.results)):
        #     story_list.append(self.actions[i])
        #     story_list.append(self.results[i])
        #
        # return "".join(story_list)

    def pop(self, *args):
        self.actions.pop(*args)
        self.results.pop(*args)

    def to_json(self):  # Invalid since I put story start as empty action
        story_dict = {}
        story_dict["story_start"] = self.story_start
        story_dict["seed"] = self.seed
        story_dict["actions"] = self.actions
        story_dict["results"] = self.results
        story_dict["choices"] = self.choices
        story_dict["possible_action_results"] = self.possible_action_results
        story_dict["game_state"] = self.game_state
        story_dict["context"] = self.context
        story_dict["uuid"] = self.uuid
        story_dict["rating"] = self.rating

        return json.dumps(story_dict)

    def save_to_local(self, save_name):
        self.uuid = str(uuid.uuid1())
        story_json = self.to_json()
        file_name = "AIDungeonSave_" + save_name + ".json"
        f = open(file_name, "w")
        f.write(story_json)
        f.close()

    def load_from_local(self, save_name):
        file_name = "AIDungeonSave_" + save_name + ".json"
        print("Save ID that can be used to load game is: ", self.uuid)

        with open(file_name, 'r') as fp:
            game = json.load(fp)
        self.init_from_dict(game)

    def save_to_storage(self):
        self.uuid = str(uuid.uuid1())

        story_json = self.to_json()
        file_name = "story" + str(self.uuid) + ".json"
        f = open(file_name, "w")
        f.write(story_json)
        f.close()
        if self.upload_story:
            FNULL = open(os.devnull, 'w')
            p = Popen(['gsutil', 'cp', file_name, 'gs://aidungeonstories'], stdout=FNULL, stderr=subprocess.STDOUT)
        return self.uuid

    def load_from_storage(self, story_id):

        file_name = "story" + story_id + ".json"
        cmd = "gsutil cp gs://aidungeonstories/" + file_name + " ."
        os.system(cmd)
        exists = os.path.isfile(file_name)

        if exists:
            with open(file_name, 'r') as fp:
                game = json.load(fp)
            self.init_from_dict(game)
            return str(self)
        else:
            return "Error save not found."


class StoryManager:

    def __init__(self, generator: GPT2Generator, debug_print=False):
        self.generator = generator
        self.story: Story = None
        self.debug_print = debug_print

    def start_new_story(self, story_prompt, context="", game_state=None, upload_story=False):
        block = self.generator.generate(context + story_prompt, debug_print=self.debug_print)
        block = cut_trailing_sentence(block)
        self.story = Story(story_prompt + block, context=context, game_state=game_state,
                           upload_story=upload_story)
        return self.story

    def load_story(self, story, from_json=False):
        if from_json:
            self.story = Story("")
            self.story.initialize_from_json(story)
        else:
            self.story = story
        return str(story)

    def json_story(self):
        return self.story.to_json()

    def story_context(self):
        return self.story.latest_result()


class UnconstrainedStoryManager(StoryManager):

    def act(self, action):
        saying = '"' in action
        prompt = f"\n> {action}\n"
        if saying:
            prompt += f"{action}\n"
        result = self.generate_result(prompt)
        if saying:
            result = f"{action}\n{result}"
        self.story.add_to_story(f"> {action}", result)
        return result

    def more_text(self):
        more_result = self.generate_result("")
        self.story.results[-1] += more_result
        return more_result

    def generate_result(self, action, use_top=False):  # non mutating
        return self.generator.generate(self.story_context() + action, debug_print=self.debug_print, use_top=use_top)

# class ConstrainedStoryManager(StoryManager):
#
#     def __init__(self, generator, action_verbs_key="classic"):
#         super().__init__(generator)
#         self.action_phrases = get_action_verbs(action_verbs_key)
#         self.cache = False
#         self.cacher = None
#         self.seed = None
#
#     def enable_caching(self, credentials_file=None, seed=0, bucket_name="dungeon-cache"):
#         self.cache = True
#         self.cacher = Cacher(credentials_file, bucket_name)
#         self.seed = seed
#
#     def start_new_story(self, story_prompt, context="", game_state=None):
#         if self.cache:
#             return self.start_new_story_cache(story_prompt, game_state=game_state)
#         else:
#             return super().start_new_story(story_prompt, context=context, game_state=game_state)
#
#     def start_new_story_generate(self, story_prompt, game_state=None):
#         super().start_new_story(story_prompt, game_state=game_state)
#         self.story.possible_action_results = self.get_action_results()
#         return self.story.story_start
#
#     def start_new_story_cache(self, story_prompt, game_state=None):
#
#         response = self.cacher.retrieve_from_cache(self.seed, [], "story")
#         if response is not None:
#             story_start = story_prompt + response
#             self.story = Story(story_start, seed=self.seed)
#             self.story.possible_action_results = self.get_action_results()
#         else:
#             story_start = self.start_new_story_generate(story_prompt, game_state=game_state)
#             self.story.seed = self.seed
#             self.cacher.cache_file(self.seed, [], story_start, "story")
#
#         return story_start
#
#     def load_story(self, story, from_json=False):
#         story_string = super().load_story(story, from_json=from_json)
#         return story_string
#
#     def get_possible_actions(self):
#         if self.story.possible_action_results is None:
#             self.story.possible_action_results = self.get_action_results()
#
#         return [action_result[0] for action_result in self.story.possible_action_results]
#
#     def act(self, action_choice_str):
#
#         try:
#             action_choice = int(action_choice_str)
#         except:
#             print("Error invalid choice.")
#             return None, None
#
#         if action_choice < 0 or action_choice >= len(self.action_phrases):
#             print("Error invalid choice.")
#             return None, None
#
#         self.story.choices.append(action_choice)
#         action, result = self.story.possible_action_results[action_choice]
#         self.story.add_to_story(action, result)
#         self.story.possible_action_results = self.get_action_results()
#         return result, self.get_possible_actions()
#
#     def get_action_results(self):
#         if self.cache:
#             return self.get_action_results_cache()
#         else:
#             return self.get_action_results_generate()
#
#     def get_action_results_generate(self):
#         action_results = [self.generate_action_result(self.story_context(), phrase) for phrase in self.action_phrases]
#         return action_results
#
#     def get_action_results_cache(self):
#         response = self.cacher.retrieve_from_cache(self.story.seed, self.story.choices, "choices")
#
#         if response is not None:
#             print("Retrieved from cache")
#             return json.loads(response)
#         else:
#             print("Didn't receive from cache")
#             action_results = self.get_action_results_generate()
#             response = json.dumps(action_results)
#             self.cacher.cache_file(self.story.seed, self.story.choices, response, "choices")
#             return action_results
#
#     def generate_action_result(self, prompt, phrase, options=None):
#
#         action_result = phrase + " " + self.generator.generate(prompt + " " + phrase, options)
#         action, result = split_first_sentence(action_result)
#         return action, result
