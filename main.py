import re
import tkinter as tk
from tkinter.filedialog import askopenfilename
import xml.etree.ElementTree as ET
import subprocess
from Dependency import Dependency

def main():
    result = subprocess.run(
        ["mvn.cmd", "dependency:tree", "-DoutputFile=dependency-tree.txt"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print("Error while running maven command")
        print(result.stderr)
        return
    explicit_dependencies = get_pom_dependencies()
    all_dependencies = flatten_dependencies(explicit_dependencies)
    for dependency in all_dependencies:
        print(dependency)


def get_pom_dependencies():
    tree = open("dependency-tree.txt", "r")
    dependencies = []
    stack = []
    for line in tree.read().split("\n"):
        if line == "":
            continue
        indentation_level = line.count("|")
        if indentation_level == 0:
            stack = []
        dependency = dependency_data_extraction(line)
        if dependency:
            while len(stack) > indentation_level:
                stack.pop()
            if stack:
                stack[-1].add_dependency(dependency)
            else:
                dependencies.append(dependency)

            stack.append(dependency)

    return dependencies

def flatten_dependencies(dependencies):
    flattened = []
    for dependency in dependencies:
        flattened.append(dependency)
        flattened.extend(flatten_dependencies(dependency.dependencies))
    return flattened

def dependency_data_extraction(line):
    dependency = line.split("-",1)[1].strip()
    print(dependency)
    pattern = r"^([a-z0-9.\-]+):([a-z0-9.\-]+):([a-z0-9.\-]+):([0-9.]+):([a-z]+)"
    match = re.match(pattern, dependency)

    if match:
        group_id = match.group(1)
        artifact_id = match.group(2)
        version = match.group(4)
        scope = match.group(5)
        return Dependency(group_id, artifact_id, version, scope)
    return None


if __name__ == "__main__":
    main()