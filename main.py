import re
import time
import tkinter as tk
from tkinter.filedialog import askopenfilename
import xml.etree.ElementTree as ET
import subprocess
import base64
import requests
from mpmath.libmp import dps_to_prec
from sqlalchemy.testing import emits_warning

from Dependency import Dependency

MAX_REQUESTS = 50
TIME_WINDOW = 30
request_timestamps = []
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
    results = check_vulnerabilities(all_dependencies)
    print_vulnerabilities(results)


def check_vulnerabilities(dependencies):
    url = "https://api.osv.dev/v1/querybatch"
    queries = []

    for dependency in dependencies:
        queries.append({
            "version": dependency.version,
            "package": {
                "name": dependency.group_id+":"+dependency.artifact_id,
                "ecosystem": "Maven",
                #"purl": f"pkg:maven/{dependency.group_id}/{dependency.artifact_id}@{dependency.version}"
            }
        })

    payload = {"queries": queries}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return parse_OSV_response(dependencies, response.json())
    else:
        return f"Error: {response.status_code}, {response.text}"

def parse_OSV_response(dependencies, response):
    results = response["results"]
    parsed_results = []
    for dependency, result in zip(dependencies,results):
        if "vulns" in result:
            vulns = result["vulns"]
            parsed_results.append({
                "dependency": f"{dependency.group_id}:{dependency.artifact_id}:{dependency.version}",
                "vulnerabilities": [f"https://github.com/advisories/{vuln["id"]}" for vuln in vulns]
            })
        else:
            parsed_results.append({
                "dependency": f"{dependency.group_id}:{dependency.artifact_id}:{dependency.version}",
                "vulnerabilities": []
            })
    return parsed_results

def print_vulnerabilities(results):
    is_found = False
    for result in results:
        if result["vulnerabilities"]:
            is_found = True
            print(f"Dependency: {result['dependency']} has vulnerabilities:{result['vulnerabilities']}")
    if is_found:
        print("Find more details using CVE identifiers available at links above")

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
    tree.close()
    return dependencies

def flatten_dependencies(dependencies):
    flattened = []
    for dependency in dependencies:
        flattened.append(dependency)
        flattened.extend(flatten_dependencies(dependency.dependencies))
    return flattened

def dependency_data_extraction(line):
    dependency = line.split("-",1)[1].strip()
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