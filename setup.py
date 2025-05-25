# Copyright 2025 Haruna5718
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import shutil
import os
import ast
import importlib.util

def extract_imports_from(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=file_path)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def is_std_lib(module_name):
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin and "site-packages" not in spec.origin:
            return True
    except:
        pass
    return False

def get_module_folder(module_name):
    try:
        mod = __import__(module_name)
        return os.path.dirname(mod.__file__)
    except:
        return None

if __name__ == "__main__":
    main_imports = extract_imports_from("main.py")

    Modules = [os.path.splitext(f)[0] for f in os.listdir("./Modules") if not f.startswith("_")]

    for Module in Modules:
        function_py_path = f"Modules/{Module}/Function.py"
        ext_modules = [
            Extension(
                "Function",
                [function_py_path]
            )
        ]

        setup(
            name=Module,
            cmdclass={'build_ext': build_ext},
            ext_modules=ext_modules,
        )

        os.remove(function_py_path.replace(".py", ".c"))
        shutil.copytree(f"Modules/{Module}", f"build/{Module}", dirs_exist_ok=True)
        os.remove(f"build/{Module}/Function.py")
        os.rename("Function.cp311-win_amd64.pyd", f"build/{Module}/Function.pyd")

        func_imports = extract_imports_from(function_py_path)
        external_modules = [
            mod for mod in func_imports
            if mod not in main_imports and not is_std_lib(mod)
        ]

        for mod in external_modules:
            mod_path = get_module_folder(mod)
            if mod_path and os.path.isdir(mod_path):
                dest = os.path.join(f"build/{Module}/Python", os.path.basename(mod_path))
                if not os.path.exists(dest):
                    shutil.copytree(mod_path, dest)
