import streamlit as st
from glob import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from html2text import html2text
from collections import defaultdict
from fuzzywuzzy import fuzz
from stqdm import stqdm
from time import sleep
import pickle
from difflib import SequenceMatcher
import re
import pandas as pd

try:
    if st.secrets["RUNNING_ONLINE"]:
        running_online = True
    else:
        running_online = False
except:
    running_online = False


def split_text(text):
    return re.findall(r'\b\w[\w\'-]*\b|\s+|[.,!?;]', text)


def highlight_differences(old_str, new_str):
    old_words = split_text(old_str)
    new_words = split_text(new_str)

    matcher = SequenceMatcher(None, old_words, new_words)
    diff = list(matcher.get_opcodes())

    highlighted_old = []
    highlighted_new = []

    for opcode, a1, a2, b1, b2 in diff:
        if opcode in ('replace', 'insert'):
            highlighted_new.extend(['<span style="color: green;">{}</span>'.format(word) for word in new_words[b1:b2]])
        if opcode in ('replace', 'delete'):
            highlighted_old.extend(['<span style="color: red;">{}</span>'.format(word) for word in old_words[a1:a2]])
        else:
            highlighted_old.extend(old_words[a1:a2])
            highlighted_new.extend(new_words[b1:b2])

    highlighted_old_str = ''.join(highlighted_old)
    highlighted_new_str = ''.join(highlighted_new)

    return highlighted_old_str, highlighted_new_str


def read_patch_dialogs(patch_former, patch_latter, write_to_cache):
    st.divider()
    dialogue_files_former = list(glob(f"data/{patch_former}/**/*.html", recursive=True))
    dialogue_files_latter = list(glob(f"data/{patch_latter}/**/*.html", recursive=True))

    former_lines_dict = defaultdict(set)
    latter_lines_dict = defaultdict(set)

    f_lines_count = 0
    for fn in stqdm(dialogue_files_former, desc=f"Processing former patch, files processed"):
        file = open(fn, "r", encoding='latin-1')
        index = file.read()
        source = BeautifulSoup(index, 'lxml')
        div_elements = source.find_all('div', class_="npc")
        for div_element in div_elements:
            character = div_element.text
            dialog_span = div_element.find_next('span', class_='dialog')
            former_lines_dict[character].add(html2text(str(dialog_span)).strip())
            f_lines_count += 1
    st.write("Former lines processed:", f_lines_count)

    l_lines_count = 0
    for fn in stqdm(dialogue_files_latter, desc=f"Processing latter patch, files processed", maxinterval=0.2):
        file = open(fn, "r", encoding='latin-1')
        index = file.read()
        source = BeautifulSoup(index, 'lxml')
        div_elements = source.find_all('div', class_="npc")
        for div_element in div_elements:
            character = div_element.text
            dialog_span = div_element.find_next('span', class_='dialog')
            latter_lines_dict[character].add(html2text(str(dialog_span)).strip())
            l_lines_count += 1
    st.write("Latter lines processed:", l_lines_count)

    if write_to_cache:
        with open("cache/former.pkl", 'wb') as file:
            pickle.dump(former_lines_dict, file)

        with open("cache/latter.pkl", 'wb') as file:
            pickle.dump(latter_lines_dict, file)

    return former_lines_dict, latter_lines_dict


def calculate_differences(former_lines_dict, latter_lines_dict):
    all_characters = set(list(former_lines_dict.keys()) + list(latter_lines_dict.keys()))
    num_changes_list = []
    for character in stqdm(all_characters, desc="Finding differences per character", maxinterval=0.2):
        lines = [l for l in latter_lines_dict[character] if l not in former_lines_dict[character]]
        new_lines = set()
        changed_lines = []
        for line in stqdm(lines, desc=f"Finding differences for {character}", maxinterval=0.2):
            for old_line in former_lines_dict[character]:
                if fuzz.ratio(line, old_line) > 80:
                    changed_lines.append((old_line, line))
                    break
            else:
                new_lines.add(line)

        num_changes = len(new_lines) + len(changed_lines)


def display_differences(differences_dict):
    summary_container = st.empty()

    st.divider()
    st.subheader("Found Differences")

    num_changes_list = []
    for character in differences_dict.keys():
        new_lines = differences_dict[character]["new"]
        changed_lines = differences_dict[character]["changed"]
        num_changes = len(new_lines) + len(changed_lines)
        if num_changes > 0:
            num_changes_list.append({"Character": character, "Number of Changes": num_changes})
            if num_changes > 1:
                expander_text = f"{character} ({num_changes} changes)"
            else:
                expander_text = f"{character} ({num_changes} change)"

            with st.expander(expander_text):
                if len(new_lines) > 0:
                    st.subheader("New Lines")
                    for idx, line in enumerate(new_lines):
                        index_col, line_col = st.columns([0.05, 0.95])
                        with index_col:
                            st.markdown(f"{idx + 1}.")

                        with line_col:
                            st.markdown(line)

                if len(changed_lines) > 0:
                    st.subheader("Changed Lines")
                    for idx, values in enumerate(changed_lines):
                        former_line, latter_line = values
                        index_col, former_line_col, arrow_col, latter_line_col = st.columns([0.05, 0.45, 0.05, 0.45])
                        old_diff_text, new_diff_text = highlight_differences(former_line, latter_line)
                        with index_col:
                            st.markdown(f"{idx + 1}.")

                        with former_line_col:
                            st.markdown(f"{old_diff_text}", unsafe_allow_html=True)

                        with arrow_col:
                            st.write("→")

                        with latter_line_col:
                            st.write(f"{new_diff_text}", unsafe_allow_html=True)

    num_changes_df = pd.DataFrame.from_dict(num_changes_list)
    with summary_container.container():
        st.divider()
        st.bar_chart(num_changes_df, x="Character", y="Number of Changes")

st.set_page_config(
        page_title="BG3 Patch Dialog Difference Tool"
    )
st.title("BG3 Patch Dialog Difference Tool")
st.markdown("<sup><b>v0.1-beta1</b> | View source code, commit history: https://github.com/Invuska/bg3-dialogdiff</sup>",
            unsafe_allow_html=True)

with st.sidebar:
    st.header("Messages")
    st.info("""This tool is in active development, as such in its current form may seem bare-bones.""", icon="ℹ️")

    st.header("Current To-Dos")
    st.info("""
    - Showing the source filename for the new/changed line
    - Add filtering and sorting options for "Found Differences"
    - Showing full dialog trees (since there's no context right now)
    - User processing - which will allow users to define their own settings such as fuzz ratio, etc. for similarity checks
    - Add option to provide your own game files (likely in an offline version)
    - Add potential graphing/summary options
    """)


patches = [v.replace("\\", '/').split('/')[1] for v in glob("data/*") if "Parser" not in v]
patches.sort()
col1, col2 = st.columns(2)
former_patch_index = 0
with col1:
    former_patch = st.selectbox("Select former patch:", patches[:-1])
    for i in range(len(patches)):
        if former_patch == patches[i]:
            former_patch_index = i
            break

with col2:
    latter_patch = st.selectbox("Select latter patch:", patches[former_patch_index + 1:])

with st.expander("Advanced Settings"):
    st.write("Please do not change these settings unless you know what you're doing.")
    st.write("For now, these settings are not available on the web version of this tool. This may change in the future.")

    if running_online:
        st.markdown("Running online: `True`. Advanced settings are disabled.")
        fuzz_ratio = st.slider("Similarity Fuzz Ratio", min_value=0, max_value=100, value=80, step=1, disabled=True)
        write_to_cache = st.checkbox("Write data to cache", value=False, disabled=True)
        read_from_cache = st.checkbox("Read from cached differences", value=True, disabled=True)
    if not running_online:
        st.markdown("Running online: `False`. Advanced settings enabled, proceed with caution")
        fuzz_ratio = st.slider("Similarity Fuzz Ratio", min_value=0, max_value=100, value=80, step=1, disabled=False)
        write_to_cache = st.checkbox("Write data to cache", value=False)
        read_from_cache = st.checkbox("Read from cached differences", value=True)

if st.button("Find Differences", use_container_width=True):
    # if read_from_cache:
    #     with open("cache/former.pkl", 'rb') as file:
    #         former = pickle.load(file)
    #
    #     with open("cache/latter.pkl", 'rb') as file:
    #         latter = pickle.load(file)
    #
    #     calculate_differences(former, latter)
    # else:
    #     former, latter = read_patch_dialogs(former_patch, latter_patch, write_to_cache)
    #     calculate_differences(former, latter)
    # calculate_differences(former, latter)
    former_patch_name, latter_patch_name = former_patch.split(" - ")[0], latter_patch.split(" - ")[0]
    try:
        with open(f"cache/cd_{former_patch_name}-{latter_patch_name}.pkl", 'rb') as file:
            differences_dict = pickle.load(file)
            display_differences(differences_dict)
    except FileNotFoundError:
        st.warning("Differences not found. If using Patch 5, currently only differences from Patch 4 to Patch 5 have been calculated. Differences from Patch 5 to other patches coming soon!")
