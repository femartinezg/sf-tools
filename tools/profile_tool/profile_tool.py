import xml.etree.ElementTree as ET
import re
import sys
import subprocess
import time
import threading

# SETTINGS (modify as needed)
AVOID_ONE_LINER = ['loginIpRanges', 'loginHours']
SORT_ORDER = {
    'Profile': ['fullName', 'description', 'custom', 'userLicense', 'loginIpRanges', 'loginHours'],
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
HELP = '''Usage: python profile_tool.py [-f] [profile_name ...]

Examples:
    python profile_tool.py Admin
    python profile_tool.py Admin "My profile" "Another profile"
    python profile_tool.py -f Admin "My profile" "Another profile" (only format)'''

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
    
    # Display help
    for arg in sys.argv[1:]:
        if arg == "-h" or arg == "--help":
            sys.exit(HELP)
        if arg == "-f" or arg == "--format":
            only_format = True

    # Profiles
    if only_format and len(sys.argv) > 2:
        profile_names = sys.argv[2:]
    elif not only_format and len(sys.argv) > 1:
        profile_names = sys.argv[1:]
    else:
        sys.exit(HELP)

    return only_format, profile_names

# Retrieve functions
def retrieve_profiles(profile_names):
    command = ['sf', 'crud-mdapi', 'read', '--metadata', *[f'Profile:{name}' for name in profile_names]]
    subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, input=b'y\n')

# Format functions
def init_xml_parser(input_path):
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Remove namespace prefixes
    for elem in root.iter():
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
        if last_elem.tag != child.tag and child.tag not in SORT_ORDER['Profile'] and last_elem.tail is not None:
            last_elem.tail = "\n" + last_elem.tail
        last_elem = child

def format_profile(input_path):
    # Formats one profile XML file
    tree, root = init_xml_parser(input_path)
    sort_inner_keys(root)
    sort_profile(root)
    ET.indent(root, space='    ')
    format_element(root)
    format_output(root)
    # Write profile
    tree.write(input_path, encoding='utf-8', xml_declaration=True)

def format_profiles(profile_names):
    for profile_name in profile_names:
        input_path = f"force-app/main/default/profiles/{profile_name}.profile-meta.xml"
        format_profile(input_path)

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
    only_format, profile_names = parse_args()

    # Retrieve profile
    if not only_format:
        stop_event, timer = init_timer("> Retrieving profiles...")
        retrieve_profiles(profile_names)
        stop_timer(stop_event, timer)

    # Format profile
    stop_event, timer = init_timer("> Formatting profiles...")
    format_profiles(profile_names)
    stop_timer(stop_event, timer)

    # Done
    print("DONE")
except KeyboardInterrupt:
    print("\nExiting...")
except subprocess.CalledProcessError as e:
    print(f"\nError: {e}\nPlease check if the profile names are correct.")
except Exception as e:
    print(f"\nUnexpected error: {e}")