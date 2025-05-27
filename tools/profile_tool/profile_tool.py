import xml.etree.ElementTree as ET
import re
import sys
import subprocess
import time
import threading
import os

# SETTINGS (modify as needed)
AVOID_ONE_LINER = ['loginIpRanges', 'loginHours']
SORT_ORDER = {
    '{http://soap.sforce.com/2006/04/metadata}Profile': ['fullName', 'description', 'custom', 'userLicense', 'loginIpRanges', 'loginHours'],
    'applicationVisibilities': ['visible', 'default', 'application'],
    'classAccesses': ['enabled', 'apexClass'],
    'customMetadataTypeAccesses': ['enabled', 'name'],
    'customPermissions': ['enabled', 'name'],
    'customSettingAccesses': ['enabled', 'name'],
    'externalDataSourceAccesses': ['enabled', 'externalDataSource'],
    'fieldPermissions': ['readable', 'editable', 'field'],
    'flowAccesses': ['enabled', 'flow'],
    'layoutAssignments': ['layout', 'recordType'],
    'loginHours': ['weekdayStart', 'weekdayEnd'],
    'loginIpRanges': ['description', 'startAddress', 'endAddress'],
    'objectPermissions': ['allowCreate', 'allowRead', 'allowEdit', 'allowDelete', 'viewAllRecords', 'modifyAllRecords', 'object', 'viewAllFields'],
    'pageAccesses': ['enabled', 'apexPage'],
    'recordTypeVisibilities': ['visible', 'default', 'personAccountDefault', 'recordType'],
    'tabVisibilities': ['visibility', 'tab'],
    'userPermissions': ['enabled', 'name']
}

# CONSTANTS
HELP = '''Usage: python profile_tool.py [-f] [-n] [profile_name ...]

Options:
  -f, --format      Format only, without retrieving profiles.
  -n, --no-clean    Do not clean the profiles, keep all the elements.

Examples:
    python profile_tool.py Admin
    python profile_tool.py Admin "My profile" "Another profile"
    python profile_tool.py -f Admin "My profile" "Another profile"
    python profile_tool.py -n Admin "My profile" "Another profile"
    python profile_tool.py -f -n Admin "My profile" "Another profile"'''

SORT_BLOCK_KEYS = {
    'applicationVisibilities': 'application',
    'classAccesses': 'apexClass',
    'customMetadataTypeAccesses': 'name',
    'customPermissions': 'name',
    'customSettingAccesses': 'name',
    'externalDataSourceAccesses': 'externalDataSource',
    'fieldPermissions': 'field',
    'flowAccesses': 'flow',
    'layoutAssignments': 'layout',
    'objectPermissions': 'object',
    'pageAccesses': 'apexPage',
    'recordTypeVisibilities': 'recordType',
    'tabVisibilities': 'tab',
    'userPermissions': 'name'
}

# FUNCTIONS
# Argument parsing functions
def parse_args():
    only_format = False
    clean = True
    profile_names = []
    
    # Display help
    for arg in sys.argv[1:]:
        if arg == "-h" or arg == "--help":
            sys.exit(HELP)
        elif arg == "-f" or arg == "--format":
            only_format = True
        elif arg == "-n" or arg == "--no-clean":
            clean = False
        elif not arg.startswith("-"):
            profile_names.append(arg)
        else:
            sys.exit(HELP)

    if not profile_names:
        sys.exit(HELP)

    return only_format, clean, profile_names

# Retrieve functions
def retrieve_profiles(profile_names):
    command = ['sf', 'crud-mdapi', 'read', '--metadata', *[f'Profile:{name}' for name in profile_names]]
    subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, input=b'y\n')

# Format functions
def init_xml_parser(input_path):
    ET.register_namespace('', 'http://soap.sforce.com/2006/04/metadata')
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Set/unset namespaces
    for elem in root.iter():
        if 'Profile' in elem.tag:
            elem.tag = '{http://soap.sforce.com/2006/04/metadata}Profile'
            break
        else:
            elem.tag = elem.tag.split('}', 1)[-1]
    
    return tree, root

def sort_inner_keys(root):
    if list(root):
        root[:] = sorted(root, key=lambda e: e.find(SORT_BLOCK_KEYS.get(e.tag)).text if e.tag in SORT_BLOCK_KEYS and e.find(SORT_BLOCK_KEYS.get(e.tag)) is not None else e.tag)

def sort_function(element, parent):
    element_tag = element.tag
    parent_tag = parent.tag
    if parent_tag in SORT_ORDER and element_tag in SORT_ORDER[parent_tag]:
        return str(SORT_ORDER[parent_tag].index(element_tag))
    return element.tag

def sort_profile(element):
    if list(element):
        element[:] = sorted(element, key=lambda e: sort_function(e, element))
        for child in element:
            sort_profile(child)

def format_element(element, level=1):
    # Format profile elements recursively to make one-liner elements
    if list(element):
        level += 1
        for child in element:
            if child.tag in AVOID_ONE_LINER:
                continue
            if level == 2:
                child.text = child.text.strip()
            if level > 2:
                child.text = child.text.strip()
                child.tail = None
            format_element(child, level)

def format_output(root):
    # Separate sections with new lines
    last_elem = root
    for child in root:
        if last_elem.tag != child.tag and child.tag not in SORT_ORDER['{http://soap.sforce.com/2006/04/metadata}Profile'] and last_elem.tail is not None:
            last_elem.tail = "\n" + last_elem.tail
        last_elem = child

def clean_output(input_path):
    script_path = os.path.dirname(os.path.abspath(__file__))
    clean_file_path = os.path.join(script_path, "rules", "profile_clean_patterns")
    include_file_path = os.path.join(script_path, "rules", "profile_include_patterns")
    lines = []
    with open(input_path, 'r', encoding='utf-8') as profile_file:
        lines = profile_file.readlines()

    clean_patterns = get_file_patterns(clean_file_path)
    inlcude_patterns = get_file_patterns(include_file_path)
    lines = clean_lines_patterns(lines, clean_patterns, inlcude_patterns)
    object_permissions = get_object_permissions(lines)
    lines = clean_missing_objects(lines, object_permissions)
    write_clean_profile(input_path, lines)

def get_file_patterns(file_path):
    patterns = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip() and not line.startswith("#"):
                patterns.append(rf"{line.strip()}")
    
    return patterns

def clean_lines_patterns(lines, clean_patterns, inlcude_patterns):
    lines_aux = []

    for line in lines:
        if not any(re.search(pattern, line) for pattern in clean_patterns):
            lines_aux.append(line)
        elif any(re.search(pattern, line) for pattern in inlcude_patterns):
            lines_aux.append(line)
    
    return lines_aux

def get_object_permissions(lines):
    object_permissions = []

    for line in lines:
        if '<objectPermissions>' in line:
            object_permissions.append(line.split('<object>')[1].split('</object>')[0])
    
    return object_permissions

def clean_missing_objects(lines, object_permissions):
    lines_aux = []

    for line in lines:
            if '<fieldPermissions>' in line:
                obj = line.split('<field>')[1].split('.')[0]
                if obj in object_permissions:
                    lines_aux.append(line)
            elif '<layoutAssignments>' in line:
                obj = line.split('<layout>')[1].split('-')[0]
                if obj in object_permissions:
                    lines_aux.append(line)
            elif '<recordTypeVisibilities>' in line:
                obj = line.split('<recordType>')[1].split('.')[0]
                if obj in object_permissions:
                    lines_aux.append(line)
            elif '<tabVisibilities>' in line:
                obj = line.split('<tab>')[1].split('</tab>')[0]
                if obj in object_permissions:
                    lines_aux.append(line)
            else:
                lines_aux.append(line)

    return lines_aux

def write_clean_profile(input_path, lines):
    with open(input_path, 'w', encoding='utf-8') as profile_file:
        previous_blank_line = False
        for line in lines:
            if not line.strip():
                if previous_blank_line:
                    continue
                previous_blank_line = True
            else:
                previous_blank_line = False
            profile_file.write(line)

def format_profile(input_path, clean):
    # Formats one profile XML file
    tree, root = init_xml_parser(input_path)
    sort_inner_keys(root)
    sort_profile(root)
    ET.indent(root, space='    ')
    format_element(root)
    format_output(root)
    # Write profile
    tree.write(input_path, encoding='utf-8', xml_declaration=True)
    # Clean profile
    if clean:
        clean_output(input_path)

def format_profiles(profile_names, clean):
    for profile_name in profile_names:
        input_path = f"force-app/main/default/profiles/{profile_name}.profile-meta.xml"
        format_profile(input_path, clean)

# Timer functions
def show_timer(message, stop_event):
    grey = "\033[90m"
    green = "\033[92m"
    endc = "\033[0m"
    start = time.time()
    while not stop_event.is_set():
        elapsed = (time.time() - start)
        print(f"\r{message} {grey}{elapsed:.2f}s{endc}", end='')
        time.sleep(0.01)
    elapsed = (time.time() - start)
    print(f"\r{message} {green}{elapsed:.2f}s{endc}", end='\n')

def init_timer(message):
    stop_event = threading.Event()
    timer = threading.Thread(target=show_timer, args=(message, stop_event), daemon=True)
    timer.start()
    return stop_event, timer

def stop_timer(stop_event, timer):
    stop_event.set()
    timer.join()

try:
    # Parse arguments
    only_format, clean, profile_names = parse_args()

    # Retrieve profile
    if not only_format:
        stop_event, timer = init_timer("> Retrieving profiles...")
        retrieve_profiles(profile_names)
        stop_timer(stop_event, timer)

    # Format profile
    stop_event, timer = init_timer("> Formatting profiles...")
    format_profiles(profile_names, clean)
    stop_timer(stop_event, timer)

    # Done
    print("\n✓ DONE")
except KeyboardInterrupt:
    print("\nExiting...")
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error: {e}\nPlease check if the profile names are correct.")
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")