# coding: utf-8
import re
from difflib import SequenceMatcher

# from functools import lru_cache
YAML_FILE = "story/story_data.yaml"


# from profanityfilter import ProfanityFilter
# pf = ProfanityFilter()

def console_print(text, width=75):
    last_newline = 0
    i = 0
    while i < len(text):
        if text[i] == "\n":
            last_newline = 0
        elif last_newline > width and text[i] == " ":
            text = text[:i] + "\n" + text[i:]
            last_newline = 0
        else:
            last_newline += 1
        i += 1
    print(text)


def get_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def get_num_options(num):
    while True:
        choice = input("Enter the number of your choice: ")
        try:
            result = int(choice)
            if result >= 0 and result < num:
                return result
            else:
                print("Error invalid choice. ")
        except ValueError:
            print("Error invalid choice. ")


def player_died(text):
    text = text.lower()
    you_dead_regexps = ["you('re| are) (dead|killed)", "you die", "you('ve| have) (died|been killed)",
                        "you \w+( yourself)? to death"]
    return any(re.search(regexp, text) for regexp in you_dead_regexps)


def player_won(text):
    won_phrases = ["live happily ever after", "you live forever"]
    for phrase in won_phrases:
        if phrase in text:
            return True
    return False


# def remove_profanity(text):
#     return pf.censor(text)


def cut_trailing_quotes(text):
    num_quotes = text.count('"')
    if num_quotes % 2 == 0:
        return text
    else:
        final_ind = text.rfind('"')
        return text[:final_ind]


def split_first_sentence(text):
    first_period = text.find('.')
    first_exclamation = text.find('!')

    if first_exclamation < first_period and first_exclamation > 0:
        split_point = first_exclamation + 1
    elif first_period > 0:
        split_point = first_period + 1
    else:
        split_point = text[0:20]

    return text[0:split_point], text[split_point:]


def cut_trailing_action(text):
    lines = text.rsplit("\n", 1)
    last_line = lines[-1]
    if re.search("you (ask|say)", last_line.lower()):
        text = "\n".join(lines[0:-1])
    return text


def result_replace(result):
    # print("\n\nBEFORE RESULT_REPLACE:")
    # print(repr(result))

    result = cut_trailing_sentence(result)
    if len(result) == 0:
        return ""
    first_letter_capitalized = result[0].isupper()
    result = result.replace('."', '".')
    result = result.replace("#", "")
    result = result.replace("*", "")
    result = result.replace("\n\n", "\n")
    # result = first_to_second_person(result)
    #         result = remove_profanity(result)

    if not first_letter_capitalized:
        result = result[0].lower() + result[1:]

    #
    # print("\n\nAFTER RESULT_REPLACE:")
    # print(repr(result))

    return result


def cut_trailing_sentence(text):
    text = standardize_punctuation(text)
    et_token = text.find("<")
    if et_token != -1:
        text = text[:et_token]
    act_token = text.find(">")
    if act_token != -1:
        text = text[:act_token]

    last_punc = max(text.rfind('.'), text.rfind("!"), text.rfind("?"))
    # if last_punc >= 0:
    text = text[:last_punc + 1]

    text = cut_trailing_quotes(text)
    text = cut_trailing_action(text)
    return text


def is_first_person(text):
    count = 0
    for pair in first_to_second_mappings:
        variations = mapping_variation_pairs(pair)
        for variation in variations:
            reg_expr = re.compile(variation[0] + '(?=([^"]*"[^"]*")*[^"]*$)')
            matches = re.findall(reg_expr, text)
            count += len(matches)

    return count > 3  # why 3??


def is_second_person(text):
    count = 0
    for pair in second_to_first_mappings:
        variations = mapping_variation_pairs(pair)
        for variation in variations:
            reg_expr = re.compile(variation[0] + '(?=([^"]*"[^"]*")*[^"]*$)')
            matches = re.findall(reg_expr, text)
            count += len(matches)

    return count > 3


def capitalize(word):
    return word[0].upper() + word[1:]


first_to_second_mappings = [
    ("I'm", "you're"),
    ("I've", "you've"),
    ("I am", "you are"),
    ("I was", "you were"),
    ("I'll", "you'll"),
    ("I'd", "you'd"),
    ("was I", "were you"),
    ("am I", "are you"),
    ("wasn't I", "weren't you"),
    ("I", "you"),
    ("my", "your"),
    ("we", "you"),
    ("we're", "you're"),
    ("mine", "yours"),
    ("me", "you"),
    ("us", "you"),
    ("our", "your"),
    ("myself", "yourself")
]

second_to_first_mappings = [
    ("you're", "I'm"),
    ("your", "my"),
    ("you are", "I am"),
    ("you were", "I was"),
    ("are you", "am I"),
    ("you", "I"),
    ("you", "me"),
    ("you'll", "I'll"),
    ("yourself", "myself"),
    ("you've", "I've")
]


def capitalize_helper(string):
    string_list = list(string)
    string_list[0] = string_list[0].upper()
    return "".join(string_list)


def capitalize_first_letters(text):
    first_letters_regex = re.compile(r'((?<=[\.\?!]\s)(\w+)|(^\w+))')

    def cap(match):
        return (capitalize_helper(match.group()))

    result = first_letters_regex.sub(cap, text)
    return result


def standardize_punctuation(text):
    text = text.replace("’", "'")
    text = text.replace("`", "'")
    text = text.replace('“', '"')
    text = text.replace('”', '"')
    return text


def replace_outside_quotes(text, current_word, repl_word):
    reg_expr = re.compile(f"(?<=\s){current_word}(?=[\s,.?!]|$)" + '(?=([^"]*"[^"]*")*[^"]*$)')
    output = reg_expr.sub(repl_word, text)
    return output


def first_to_second_person(text):
    text = " " + text
    text = standardize_punctuation(text)
    for pair in first_to_second_mappings:
        variations = mapping_variation_pairs(pair)
        for variation in variations:
            text = replace_outside_quotes(text, variation[0], variation[1])

    return capitalize_first_letters(text[1:])


def capitalize_i(text):
    text = " " + text
    reg_expr = re.compile("(?<=\s)i(?=[\s,.?!']|$)")
    text = reg_expr.sub("I", text)
    return capitalize_first_letters(text[1:])


def second_to_first_person(text):
    text = " " + text + " "
    text = standardize_punctuation(text)
    for pair in second_to_first_mappings:
        variations = mapping_variation_pairs(pair)
        for variation in variations:
            text = replace_outside_quotes(text, variation[0], variation[1])

    return capitalize_first_letters(text[1:-1])


# @lru_cache()
def mapping_variation_pairs(mapping):
    mapping_list = [mapping]

    def maybe_map(mp, mp2=mapping[1]):
        for x in mapping_list:
            if x[0] == mp:
                return
        mapping_list.append((mp, mp2))

    maybe_map(mapping[0].lower())
    maybe_map(capitalize(mapping[0]), capitalize(mapping[1]))
    maybe_map(mapping[0].replace("'", ""))
    maybe_map(mapping[0].replace("'", "").lower())

    # Change you it's before a punctuation
    # if mapping[0] == "you":
    #     mapping = ("you", "me")
    #     mapping_list.append(("(?<=\s)" + mapping[0] + "(?=[\s,.?!])", mapping[1]))

    return mapping_list
