import re
import subprocess
from copy import deepcopy

import requests
from collections import defaultdict, OrderedDict
from Dependency import Dependency, OmittedDependency

MAX_REQUESTS = 50
TIME_WINDOW = 30
request_timestamps = []
def main():
    result = subprocess.run(
        ["mvn.cmd", "dependency:tree","-Dverbose", "-DoutputFile=dependency-tree.txt"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print("Error while running maven command")
        print(result.stderr)
        return
    explicit_dependencies = get_pom_dependencies()
    all_dependencies = flatten_dependencies(explicit_dependencies)
    results = check_vulnerabilities(all_dependencies)
    print_vulnerabilities(results)
    conflicts = analyze_dependencies(explicit_dependencies)
    suggestions = suggest_resolution(conflicts)
    print("\nConflicts found:")
    for suggestion in suggestions:
        print(suggestion)


def suggest_resolution(conflicts):
    """
    Proponuje rozwiązania konfliktów, informując o ich źródłach.
    """
    suggestions = []
    for key, versions_map in conflicts.items():
        # Znajdujemy najnowszą wersję jako sugerowane rozwiązanie
        latest_version = max(versions_map.keys())

        # Informacje o źródłach wersji
        sources_info = "\n".join(
            f"  - Version {version} introduced by: {' -> '.join(sources)}" for version, sources in versions_map.items()
        )

        # Dodajemy sugestię wraz z pełnymi informacjami
        suggestion = (
            f"\nConflict for {key}:\n"
            f"Suggested version: {latest_version}\n"
            f"Version details:\n{sources_info}"
        )
        suggestions.append(suggestion)

    return suggestions

def analyze_dependencies(dependencies):
    """
    Analyzuje zależności i wykrywa konflikty wersji.
    Cofamy się do ostatniej zależności, która może prowadzić do innych zależności,
    i usuwamy zależność, którą już przetworzyliśmy w tej samej wersji.
    """
    path_stack = []  # Stos ścieżek zależności
    seen_sub_dependencies = set()
    dependency_map = defaultdict(lambda: defaultdict(list))

    def process_dependencies(dep, source):
        key = f"{dep.group_id}:{dep.artifact_id}"
        path_stack.append(""+source) # adding dependency to path
        if key in seen_sub_dependencies:
            path_stack.pop()
            return
        seen_sub_dependencies.add(key)
        for sub_dep in dep.dependencies:
            process_dependencies(sub_dep, key)

        # end of search in sub-dependencies
        dependency_map[key][dep.version] = list(path_stack)
        path_stack.pop()

    for dep in dependencies:
        process_dependencies(dep, "direct dependency")
        seen_sub_dependencies.clear()

    # Wykrywamy konflikty (więcej niż jedna wersja dla jednego artefaktu)
    conflicts = {}
    for key, versions_map in dependency_map.items():
        if len(versions_map) > 1:
            conflicts[key] = versions_map

    return conflicts


def check_vulnerabilities(dependencies):
    url = "https://api.osv.dev/v1/querybatch"
    queries = []
    requested = OrderedDict()
    for dependency in dependencies:
        id = f"{dependency.group_id}:{dependency.artifact_id}:{dependency.version}"
        if id in requested:
            continue
        requested[id] = dependency
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
        return parse_OSV_response(requested.values(), response.json())
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
                "vulnerabilities": [f"https://github.com/advisories/{vuln['id']}" for vuln in vulns]
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
        indentation_level =(len(line) - len(line.lstrip(" +-|\\"))) // 3  # 3 spacje = 1 poziom
        if indentation_level == 0:
            stack = []
        dependency = dependency_data_extraction(line)
        if dependency:
            while len(stack) > indentation_level-1:
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
    """Ekstrakcja danych zależności z linii, w tym zależności omitted."""
    # Sprawdzenie, czy linia zawiera informację o "omitted"
    if "duplicate" in line:
        return None
    omitted_match = re.search(r"\(.*?omitted for (conflict with ([0-9.]+))\)", line)
    omitted_version = omitted_match.group(1) if omitted_match else None
    clean_line = line.split("-",1)[1].strip(" ()")

    # Wzorzec dla zwykłej zależności
    pattern = r"^([a-zA-Z0-9.\-]+):([a-zA-Z0-9.\-]+):([a-zA-Z0-9.\-]+):([0-9.]+):([a-z]+)"
    match = re.match(pattern, clean_line)

    if match:
        group_id = match.group(1)
        artifact_id = match.group(2)
        version = match.group(4)
        scope = match.group(5)

        # Jeśli zależność była oznaczona jako omitted, zwróć obiekt klasy OmittedDependency
        if omitted_version:
            return OmittedDependency(group_id, artifact_id, version, scope, omitted_version)

        # Zwróć zwykły obiekt Dependency
        return Dependency(group_id, artifact_id, version, scope)

    # Zwróć None, jeśli linia nie pasuje do wzorca
    return None


if __name__ == "__main__":
    main()