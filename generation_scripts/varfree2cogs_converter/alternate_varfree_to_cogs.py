# an alternative script for converting variable free LFs to Cogs LFs
import re
import regex
from collections import defaultdict
import json
import pandas as pd
import sys
import string
from itertools import chain


with open('lexicon/verbs2lemmas.json') as lemma_file:
 verbs_lemmas = json.load(lemma_file)

with open('lexicon/proper_nouns.json') as propN_file:
 proper_nouns = json.load(propN_file)

verb_dict = dict()
for filename in ["V_trans.json", "V_unacc.json", "V_unerg.json"]:
    with open("lexicon/" + filename) as f:
        vlist = json.load(f)
        key = filename.split(".")[0]
        verb_dict[key] = vlist

all_verbs = [verb for l in list(verb_dict.values()) for verb in l ]
                 
with open('lexicon/nouns.json') as N_file:
    nouns = json.load(N_file)
    

# recursive parsing algorithm

# step 1: generate parsing tree
def gen_tree(variable_free_lf):

    # generate an LF tree:
    """
    Generate a tree for the LF. 
    The tree is structured as follows:

    """


    lf_list = variable_free_lf.split(" ")

    depth = 0

    depth_lists = [[]]

    for elem in lf_list:
        if elem in ["=", ",", "*"]:
            pass
        elif elem == "(":
            depth += 1
            if  depth > len(depth_lists) - 1:
                depth_lists.append([])
        elif elem == ")":
            depth_lists[depth-1].append(depth_lists[depth])
            depth_lists[depth] = []
            depth -= 1
        else:
            depth_lists[depth].append(elem)


    return depth_lists[0]

# step 2: identify individuals and variables
def gen_ix_list(variable_free_lf):
    lf_list = variable_free_lf.split(" ")

    ix_dict = {"definite": dict(),
               "indefinite": dict(),
               "allN": dict()}

    ix = 0

    var_ix = 0

    while ix < len(lf_list):
        if lf_list[ix] in ["*"]:
            ix += 1

            ix_dict["definite"][lf_list[ix]] = "x _ " + str(var_ix)
            ix_dict["allN"][lf_list[ix]] = "x _ " + str(var_ix)

            ix += 1
            var_ix += 1
        elif lf_list[ix] in nouns:
            ix_dict["indefinite"][lf_list[ix]] = "x _ " + str(var_ix)
            ix_dict["allN"][lf_list[ix]] = "x _ " + str(var_ix)

            ix += 1
            var_ix += 1
        else:
            ix += 1
        
    return ix_dict, var_ix




# step 3: parse and translate
def parse_and_translate(lf_tree, ix_dict, last_ix):
    pass
    """
    recursive function for parsing LFs with conjunction

    Head categories:
    - Logical connectives: and - connects two things of Event type
    - Events/verbs 


    returns: COGS lf string, last used index + 1
    """

    ix_nouns = ix_dict["allN"]

    current_ix = last_ix

    if len(lf_tree) == 1:
        item = lf_tree[0]

        if item in proper_nouns:
            return item, current_ix
        elif item in ix_nouns.keys():
            return ix_nouns[item], current_ix
        
    else:
        head = lf_tree[0]
        daughters = lf_tree[1]

        if head == "and":
            
            # Conjunction of events -> expected shape [j1, v1, [vargs], j2, v2, [vargs]]
            if len(daughters) != 6:
                pass # Should throw an exception here
            else:
                text_j1, ix_j1 = parse_and_translate(daughters[1:3], ix_dict, current_ix)
                text_j2, ix_j2 = parse_and_translate(daughters[4:],  ix_dict, ix_j1)

                return text_j1 + " AND " + text_j2, ix_j2


        elif head in all_verbs:
            event_ix = "x _ " + str(current_ix)
            current_ix += 1

            num_v_args = len(daughters) / 2 # assuming all arguments are nominals

            arg_num = 0

            out_text = ""

            while arg_num < num_v_args:
                suffix = daughters[arg_num * 2]
                arg_tree = daughters[arg_num * 2 + 1]
                
                if isinstance(arg_tree, str):
                    arg_tree = [arg_tree]

                arg_text, current_ix = parse_and_translate(arg_tree, ix_dict, current_ix)

                out_text = out_text + head + " . " +  suffix + " ( " + event_ix + " , " + arg_text + " )"

                arg_num += 1 
                if arg_num < num_v_args:
                    out_text = out_text + " AND "
                
            return out_text, current_ix
                

def variable_free_to_cogs(variable_free_lf):
    """
    Input: A variable free LF string
    Output: A COGS LF string
    """

    lf_tree = gen_tree(vf_lf)
    ix_dict, current_ix = gen_ix_list(vf_lf)

    lfstring1 = ""

    definites = ix_dict["definite"].items()
    indefinites = ix_dict["indefinite"].items()

    for key, value in definites:
        lfstring1 = lfstring1 + "* " + key + " ( " + value + " ) ; "

    for key, value in indefinites:
        lfstring1 = lfstring1 + key + " ( " + value + " ) AND "

    lfstring2, _ = parse_and_translate(lf_tree, ix_dict, current_ix)

    return lfstring1 + lfstring2



if __name__ == "__main__":

    # print(gen_tree("like ( agent = * governor , theme = director ( nmod = award ( agent = * lawyer , theme = donut , recipient = director ) ) )"))

   
    # print(gen_ix_list("sleep ( agent = Ava )"))
    # print(gen_ix_list("and ( junct1 = sleep ( agent = girl ) , junct2 = sleep ( agent = Aubrey ) )"))

    vf_lf = "and ( junct1 = sleep ( agent = girl ) , junct2 = sleep ( agent = Aubrey ) )"
    cogs_lf = variable_free_to_cogs(vf_lf)

    print(cogs_lf)