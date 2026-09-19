from BaseClasses import MultiWorld
from Options import PerGameCommonOptions
from rule_builder.rules import Has
from ..AutoWorld import World
from .ParseJSON import location_name_to_req, item_name_to_id
from math import floor
import re

import logging
logger = logging.getLogger()

def set_rules(multiworld: MultiWorld, world: World, options: PerGameCommonOptions, player: int):
    world.set_completion_rule(Has("Bounty", required_bounties(options, world)))

def required_bounties(options: PerGameCommonOptions, world: World) -> int:
    return max(floor((options.goal_requirement.value/100) * len(world.enabled_albums)), 1)

ITEM_REGEX = re.compile(r"(\|[^|]*\|)") #matches |anything|
MACRO_REGEX = re.compile(r"(\|@[^|]*\|)") #matches |@anything|
AND_REGEX = re.compile(r'\s?\bAND\b\s?', re.IGNORECASE)
OR_REGEX = re.compile(r'\s?\bOR\b\s?', re.IGNORECASE)
DIGITS_REGEX = r"[0-9]"

# This function was written by DNVIC for sm64hacks
# Was given permission to use it :)
def parse_requirement_string_to_postfix(string: str) -> tuple[list[str], list[str]] | None:
    requirements = re.findall(ITEM_REGEX, string)
    for index, requirement in enumerate(requirements):
        string = string.replace(requirement, str(index), 1)
    string = re.sub(r" and ", "&", string, flags=re.IGNORECASE)
    string = re.sub(r" or ", "|", string, flags=re.IGNORECASE)
    string = string.replace("\n", "")
    string = string.replace(" ", "")
    print(string, requirements)
    stack = []
    result = []
    skip = []
    for index, character in enumerate(string): #converting infix to postfix
        if(index in skip):
            continue
        number = ""
        if(re.match(DIGITS_REGEX, character)):
            number += character
            while index + 1 < len(string) and re.match(DIGITS_REGEX, string[index + 1]):
                index += 1
                skip.append(index)
                number += string[index]
            result.append(number)
        elif character == '(':
            stack.append('(')
        elif character == ')':
            while stack[-1] != '(':
                result.append(stack.pop())
            stack.pop()
        else:
            while len(stack) > 0 and character == '|' and stack[len(stack) - 1] == '&':
                result.append(stack.pop())
            stack.append(character)
    while len(stack) > 0:
        result.append(stack.pop())
    return result, requirements

def evaluate_postfix_requirements(postfix: list[str], requirements: list[str], location: str, prog_items: dict) -> bool:
    print(postfix, requirements, location)
    stack = []
    for token in postfix:
        if token == '&':
            value1 = stack.pop()
            value2 = stack.pop()
            stack.append(value1 & value2)
        elif token == '|':
            value1 = stack.pop()
            value2 = stack.pop()
            stack.append(value1 | value2)
        else:
            item = requirements[int(token)]
            if re.match(ITEM_REGEX, item) == None:
                raise ValueError(f"Requirements for location {location} have an item without pipes")
            item, amount = item_is_real(item, location)
            if item in prog_items.keys():
                prog_items[item] = max(amount, prog_items[item])
            else:
                prog_items[item] = amount
            stack.append(Has(item, amount))
    return stack.pop(), prog_items

def item_is_real(item: str, location: str):
    item = item.strip('|')
    g = item.split(':')
    num = 1
    if len(g) == 2:
        if not g[1].isdigit():
            raise ValueError(f"Value for amount of item {item} is not numeric for location {location}")
        num = int(g[1])
        item = g[0]
    if item in item_name_to_id.keys():
        return [item, num]
    else:
        raise ValueError(f"Unknown item {item} for location {location}")

def fake_set_rules(multiworld: MultiWorld, world: World, options: PerGameCommonOptions, player:int):
    prog_items = {}
    sphere_1_albums = []

    # Check all locs for requirements
    all_locations = multiworld.get_locations(player)
    for loc in all_locations:
        reqs = location_name_to_req[loc.name]
    
        if reqs != "":
            result, requirements = parse_requirement_string_to_postfix(reqs)
            state, prog_items = evaluate_postfix_requirements(result, requirements, loc, prog_items)
            world.set_rule(loc, state)
        else:
            if loc.parent_region.name not in sphere_1_albums:
                sphere_1_albums.append(loc.parent_region.name)

    return prog_items, sphere_1_albums
