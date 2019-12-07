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
    choice = get_num_options(len(settings) + 1)

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
    character_key = list(characters)[get_num_options(len(characters))]

    name = input("\nWhat is your name? ").title() or "Akababa"
    setting_description = data["settings"][setting_key]["description"]
    character = data["settings"][setting_key]["characters"][character_key]

    context = "You are " + name + ", a " + character_key + " " + setting_description + \
              "You have a " + character["item1"] + " and a " + character["item2"] + ". "
    prompt_num = np.random.randint(0, len(character["prompts"]))
    prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc."'
    text += '\n To speak enter \'say "(thing you want to say)"\' or just "(thing you want to say)" (with quotes!!)'
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

    upload_story = False

    print("\nInitializing AI Dungeon! (This might take a few minutes)\n")
    generator = GPT2Generator(generate_num=args.len)
    story_manager = UnconstrainedStoryManager(generator, debug_print=args.debug)
    print("\n")

    with open('opening.txt', 'r', encoding="utf-8") as file:
        starter = file.read()
    print(starter)

    while True:
        if story_manager.story != None:
            del story_manager.story

        print("\n\n")
        context, prompt = select_game()
        console_print(instructions())
        print("\nGenerating story...")

        story_manager.start_new_story(prompt, context=context, upload_story=upload_story)

        print("\n")
        console_print(str(story_manager.story))
        while True:
            # tcflush(sys.stdin, TCIFLUSH)
            sys.stdin.flush()
            action = input("> ").strip()
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
                upload_story = False
                story_manager.story.upload_story = False
                console_print("Saving turned off.")

            elif action == "help":
                console_print(instructions())

            elif action == "save":
                if upload_story:
                    id = story_manager.story.save_to_storage()
                    console_print("Game saved.")
                    console_print("To load the game, type 'load' and enter the following ID: " + id)
                else:
                    console_print("Saving has been turned off. Cannot save.")

            elif action == "load":
                load_ID = input("What is the ID of the saved game?")
                result = story_manager.story.load_from_storage(load_ID)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif len(action.split(" ")) == 2 and action.split(" ")[0] == "load":
                load_ID = action.split(" ")[1]
                result = story_manager.story.load_from_storage(load_ID)
                console_print("\nLoading Game...\n")
                console_print(result)

            elif action == "print":
                print("\nPRINTING\n")
                print(str(story_manager.story))

            elif action == "revert":

                if len(story_manager.story.actions) == 0:
                    console_print("You can't go back any farther. ")
                    continue

                story_manager.story.actions.pop()
                story_manager.story.results.pop()
                console_print("Last action reverted. ")
                if len(story_manager.story.results) > 0:
                    console_print(story_manager.story.results[-1])
                else:
                    console_print(story_manager.story.story_start)
                continue

            elif len(action.split()) >= 2 and action.split()[0] in ["query", "queryy"]:
                queryy, question = action.split(maxsplit=1)
                if question[-1] != '?':
                    question += '?'
                if queryy == "queryy":
                    question = first_to_second_person(question)
                else:
                    question = capitalize_i(question)
                question = "\nQ: " + question + "\n"
                answer = story_manager.generate_result(question, use_top=True)
                answer = answer.strip().split("\n")[0]  # gonna be a bunch of alternating Q: A: lines
                # if answer[:3] == "A: ":
                #     answer = answer[3:]
                console_print(question + answer)

            elif len(action.split()) >= 2 and action.split()[0] in ["debug", "debugt"]:
                debugt, action = action.split(maxsplit=1)
                action = bytes(action, "utf-8").decode("unicode_escape")
                # action = action.replace("\\n", "\n")  # experiment with newlines
                answer = story_manager.generate_result(action, use_top=debugt == "debugt")
                console_print(answer)
            else:
                if action != "":
                    action = action[0].lower() + action[1:]
                    if action[0] == '"':
                        action = f'say {action}'
                    elif action[0:4].lower() == "say ":
                        quote = action.split(maxsplit=1)[1]
                        if quote[0] != '"':
                            action = f'say "{quote}"'
                    if action[0:2].lower() not in ['i ', "i'"]:  # don't input i
                        action = "I " + action
                    action = first_to_second_person(action)
                    if args.inline:
                        action = "\n" + action
                    else:
                        if action[-1] not in [".", "?", "!"]:
                            action = action + "."
                        action = f"\n> {action}\n"

                    console_print(action)
                # if args.debug:
                #     console_print("\n******DEBUG FULL ACTION*******")
                #     console_print(action)
                #     console_print("******END DEBUG******\n")
                result = story_manager.act(action)
                if args.inline:
                    result = action + result
                if len(story_manager.story.results) >= 2:
                    similarity = get_similarity(story_manager.story.results[-1], story_manager.story.results[-2])
                    if similarity > 0.9:
                        story_manager.story.actions = story_manager.story.actions[:-1]
                        story_manager.story.results = story_manager.story.results[:-1]
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
    args.add_argument("--len", type=int, default=120)
    args.add_argument("--inline", action="store_true", help="inline actions")
    args = args.parse_args()
    play_aidungeon_2()
