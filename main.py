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
    namespace = {'pom': root.tag.split("}")[0].strip("{")}
    dependencies = root.find("pom:dependencies", namespace).findall("pom:dependency", namespace)
    result = {}
    for dependency in dependencies:
        name = dependency.find("pom:artifactId", namespace).text
        atributes = {
            "groupId":
            dependency.find("pom:groupId", namespace).text if dependency.find("pom:groupId",
                                                                              namespace) is not None else "",
            "version":
            dependency.find("pom:version", namespace).text if dependency.find("pom:version",
                                                                              namespace) is not None else "",
            "scope":
            dependency.find("pom:scope", namespace).text if dependency.find("pom:scope", namespace) is not None else "compile"
        }
        result[name] = atributes

    parent = root.find("pom:parent", namespace)
    if parent is not None:
        for key in result:
            if result[key]["groupId"] == parent.find("pom:groupId", namespace).text and result[key]["version"] == "":
                result[key]["version"] = parent.find("pom:version", namespace).text
    return result




if __name__ == "__main__":
    main()