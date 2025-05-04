# Profile Tool - Simplify Salesforce Profile Management

`profile_tool.py` is a Python script designed to retrieve and format Salesforce profile metadata. It simplifies the process of managing and organizing profile XML files by applying consistent formatting and sorting rules.

## Why Use It

- Simplifies the maintenance of **complete profiles** in a Salesforce org by **avoiding differences in formatting** and element ordering.
- Helps developers by **reducing and simplifying** potential **conflicts**.
- Enforces consistent formatting across teams, improving collaboration.

## Requirements

- Python 3.x
- Salesforce CLI (`sf`) installed and authenticated.
- [sfdx-plugin-source-read](https://github.com/amtrack/sfdx-plugin-source-read) installed.

## Usage

Run the script with the following syntax:

```bash
python profile_tool.py [-f] [profile_name ...]
```

> [!IMPORTANT]
> If you are using **VSCode**, it is recommended to change the following settings:
>
> - Set "Diff Algorithm" and "Merge Algorithm" to 'legacy'.
> - Set "Diff Editor: Max Computation Time" to 0.
>
> These changes are suggested because profile files are very large and may cause issues with standard options.

### Examples

1. Retrieve and format profiles:
   ```bash
   python profile_tool.py Admin
   python profile_tool.py Admin "My profile" "Another profile"
   ```

2. Format profiles only (skip retrieval):
   ```bash
   python profile_tool.py -f Admin "My profile" "Another profile"
   ```

### Options

- `-f`, `--format`: Only format the profiles without retrieving them.
- `-h`, `--help`: Display the help message.

## Configuration

The script includes customizable settings:

- **`AVOID_ONE_LINER`**: List of XML tags to avoid formatting as one-liners.
- **`SORT_ORDER`**: Dictionary defining the sorting order for XML elements.