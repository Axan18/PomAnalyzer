import tkinter as tk
from tkinter.filedialog import askopenfilename
import xml.etree.ElementTree as ET

def main():
    dependencies = get_pom_dependencies()
    print(dependencies)

def get_pom_dependencies():
    # TODO: encable this code to select file from dialog
    #tk.Tk().withdraw()
    #pom_file = askopenfilename(title="Select pom.xml file", filetypes=[("XML files", "*.xml")])
    #tree = ET.parse(pom_file)
    tree = ET.parse("example_pom.xml")
    root = tree.getroot()
    global namespace
    namespace = {'pom': root.tag.split("}")[0].strip("{")}
    dependencies = root.find("pom:dependencies", namespace).findall("pom:dependency", namespace)
    result = {}
    for dependency in dependencies:
        name, attributes = dependency_parser(dependency)
        result[name] = attributes

    parent = root.find("pom:parent", namespace)
    if parent is not None:
        parent = dependency_parser(parent)
        result = dependency_version_from_parent(result, parent[1])
    return result

def dependency_parser(dependency) -> tuple:
    name = dependency.find("pom:artifactId", namespace).text
    atributes = {
        "groupId":
            dependency.find("pom:groupId", namespace).text if dependency.find("pom:groupId",
                                                                              namespace) is not None else "",
        "version":
            dependency.find("pom:version", namespace).text if dependency.find("pom:version",
                                                                              namespace) is not None else "",
        "scope":
            dependency.find("pom:scope", namespace).text if dependency.find("pom:scope",
                                                                            namespace) is not None else "compile"
    }
    return name, atributes
def dependency_version_from_parent(dependencies, parent):
    for key in dependencies:
        if dependencies[key]["groupId"] == parent["groupId"] and dependencies[key]["version"] == "":
            dependencies[key]["version"] = parent["version"]
    return dependencies


if __name__ == "__main__":
    main()