from story.story_manager import *
from generator.gpt2.gpt2_generator import *
from story.utils import *
import yaml
import sys, os
import argparse
import numpy as np

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


def select_game():
    with open(YAML_FILE, 'r') as stream:
        data = yaml.safe_load(stream)

    print("Pick a setting.")
    settings = data["settings"].keys()
    for i, setting in enumerate(settings):
        print_str = str(i) + ") " + setting
        if setting == "fantasy":
            print_str += " (recommended)"

        console_print(print_str)
    console_print(str(len(settings)) + ") custom")
    choice = 0 if args.defaults else get_num_options(len(settings) + 1)

    if choice == len(settings):
        context = ""
        console_print("\nEnter a prompt that describes who you are and the first couple sentences of where you start "
                      "out ex:\n 'You are a knight in the kingdom of Larion. You are hunting the evil dragon who has been " +
                      "terrorizing the kingdom. You enter the forest searching for the dragon and see' ")
        prompt = input("Starting Prompt: ")
        return context, prompt

    setting_key = list(settings)[choice]

    print("\nPick a character")
    characters = data["settings"][setting_key]["characters"]
    for i, character in enumerate(characters):
        console_print(str(i) + ") " + character)
    character_key = list(characters)[0 if args.defaults else get_num_options(len(characters))]

    name = "Akababa" if args.defaults else input("\nWhat is your name? ").title()
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    context = f"Your name is {name}, and you are a {character_key} {setting_description}" \
              f"You have a {character['item1']} and a {character['item2']}. "
    prompt_num = np.random.randint(0, len(character["prompts"]))
    prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc."'
    text += '\n To speak enter \'say (thing you want to say)\' (without quotes), but it works better if you ' \
            'write something without dialogue like \'tell him about your dream\'.'
    text += '\n\nThe following commands can be entered for any action: '
    text += '\n  "revert"   Reverts the last action allowing you to pick a different action.'
    text += '\n  "quit"     Quits the game and saves'
    text += '\n  "restart"  Starts a new game and saves your current one'
    text += '\n  "save"     Makes a new save of your game and gives you the save ID'
    text += '\n  "load"     Asks for a save ID and loads the game if the ID is valid'
    text += '\n  "print"    Prints a transcript of your adventure (without extra newline formatting)'
    text += '\n  "query"    Ask a question without advancing the story (ex: what is my name)'
    text += '\n  "debug"    Input literal'
    text += '\n  "help"     Prints these instructions again'
    return text


def play_aidungeon_2():
    console_print("AI Dungeon 2 will save and use your actions and game to continually improve AI Dungeon."
                  + " If you would like to disable this enter 'nosaving' for any action. This will also turn off the "
                  + "ability to save games.")

    print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    generator = GPT2Generator(generate_num=args.len, top_k=args.top_k, top_p=args.top_p, temperature=args.temp,
                              penalty=args.penalty)
    story_manager = UnconstrainedStoryManager(generator, debug_print=args.debug)
    print("\n")

    with open('opening.txt', 'r', encoding="utf-8") as file:
        starter = file.read()
    print(starter)

    while True:
        print("\n\n")
        if args.load:
            story_manager.story = Story("")
            story_manager.story.load_from_storage(args.load)
        else:
            context, prompt = select_game()
            print("\nGenerating story...")
            story_manager.start_new_story(prompt, context=context)

        console_print(instructions())
        console_print(str(story_manager.story))
        while True:
            sys.stdin.flush()
            action_raw = input("> ")
            action = action_raw.strip()
            if action == "restart":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                break

            elif action == "quit":
                rating = input("Please rate the story quality from 1-10: ")
                rating_float = float(rating)
                story_manager.story.rating = rating_float
                exit()

            elif action == "nosaving":
                story_manager.story.upload_story = False
                console_print("Saving turned off.")

            elif action == "help":
                console_print(instructions())

            elif action == "save":
                save_id = story_manager.story.save_to_storage()
                console_print("Game saved.")
                console_print("To load the game, type 'load' and enter the following ID: " + save_id)

            elif action == "load":
                load_id = input("What is the ID of the saved game?")
                result = story_manager.story.load_from_storage(load_id)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif len(action.split(" ")) == 2 and action.split(" ")[0] == "load":
                load_id = action.split(" ")[1]
                result = story_manager.story.load_from_storage(load_id)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif action == "print":
                console_print(str(story_manager.story))

            elif action == "revert":

                if len(story_manager.story.actions) <= 1:
                    console_print("You can't go back any farther. ")
                    continue

                story_manager.story.pop()
                console_print("Last action reverted. ")
                console_print(story_manager.story.results[-1])
                continue

            elif len(action.split()) >= 2 and action.split()[0] in ["query", "queryi"]:
                query_type, question = action.split(maxsplit=1)
                if question[-1] != '?':
                    question += '?'
                if query_type == "query":  # default
                    question = first_to_second_person(question)
                else:
                    question = capitalize_i(question)
                question = "\n> Q: " + question + "\nA:"  # Adding the space after A: messes up BPE, for ex. when asking for my name.
                console_print(question)
                answer = story_manager.generate_result(question, use_top=True, postprocess=False)
                answer = answer.strip().split("\n", 1)[0]  # gonna be a bunch of alternating Q: A: lines
                console_print(answer)

            elif len(action.split()) >= 2 and action.split()[0] in ["debug", "debugt"]:
                debugt, action = action_raw.split(maxsplit=1)
                action = bytes(action, "utf-8").decode("unicode_escape")
                answer = story_manager.generate_result(action, use_top=debugt == "debugt", postprocess=False)
                console_print(answer)
            else:
                if action == "":
                    result = story_manager.more_text()
                else:
                    action = action[0].lower() + action[1:]
                    if action[-1] not in '.?!':
                        action += '.'
                    if action[0:4].lower() == "say ":
                        quote = action.split(maxsplit=1)[1]
                        quote = quote[0].upper() + quote[1:]
                        action = f'say "{quote}"'
                    if action[0:2].lower() not in ['i ', "i'"]:  # don't input i
                        action = "I " + action
                    action = first_to_second_person(action)

                    console_print(action)
                    result = story_manager.act(action)

                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(story_manager.story.results[-1], story_manager.story.results[-2])
                    if similarity > 0.9:
                        story_manager.story.pop()
                        console_print(
                            "Woops that action caused the model to start looping. Try a different action to prevent that.")
                        continue

                if player_won(result):
                    console_print(result + "\n CONGRATS YOU WIN")
                    break
                elif player_died(result):
                    console_print(result)
                    console_print("YOU DIED. GAME OVER")
                    console_print("\nOptions:")
                    console_print('0) Start a new game')
                    console_print('1) "I\'m not dead yet!" (If you didn\'t actually die) ')
                    console_print('Which do you choose? ')
                    choice = get_num_options(2)
                    if choice == 0:
                        break
                    else:
                        console_print("Sorry about that...where were we?")
                        console_print(result)

                else:
                    console_print(result)


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument("--debug", action="store_true")
    args.add_argument("--defaults", action="store_true")
    args.add_argument("--len", type=int, default=120)
    args.add_argument("--top_k", type=int, default=None)
    args.add_argument("--top_p", type=float, default=0.7)
    args.add_argument("--temp", type=float, default=0.7)
    args.add_argument("--penalty", type=float, default=0.1, help="penalty for repeated tokens")
    args.add_argument("--load", type=str, help="id to load")
    args = args.parse_args()
    play_aidungeon_2()
