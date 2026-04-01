import ast
import os
import sys
import sysconfig

def get_stdlib_modules():
    stdlib_modules = set(sys.builtin_module_names)
    try:
        stdlib_modules.update(sys.stdlib_module_names)
    except AttributeError:
        # Fallback for Python < 3.10
        import distutils.sysconfig as sysconfig
        std_lib_path = sysconfig.get_python_lib(standard_lib=True)
        for name in os.listdir(std_lib_path):
            if name.endswith('.py'):
                stdlib_modules.add(name[:-3])
            elif os.path.isdir(os.path.join(std_lib_path, name)):
                stdlib_modules.add(name)
    return stdlib_modules

stdlib = get_stdlib_modules()
local_modules = {'app', 'tests', 'alembic', 'backend'}

external_imports = set()

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                base = n.name.split('.')[0]
                if base not in stdlib and base not in local_modules:
                    external_imports.add(base)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base = node.module.split('.')[0]
                if base not in stdlib and base not in local_modules and node.level == 0:
                    external_imports.add(base)

import glob
for filepath in glob.glob(r'c:\Users\ragha\Trading-Platform\backend\**\*.py', recursive=True):
    # Ignore venv
    if 'venv' in filepath or '.venv' in filepath:
        continue
    parse_file(filepath)

print("EXTERNAL IMPORTS:")
for imp in sorted(external_imports):
    print(imp)
