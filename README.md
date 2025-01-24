# PomAnalyzer

---

## General info
Application purpose is to help manage Apache Maven dependencies in pom.xml file (especially for Java enviornment).

App analizes all dependencies in pom.xml including transactive dependencies. Every dependency is checked if it has any vulnerabilites with use of https://github.com/google/osv.dev. In the next step conflicts between dependencies are detected and path leading to them is presented.

## Technologies
* Python
* Maven

## Setup
1. Clone the repository
2. Run it with python main.py

## Possible upgrades
* More test pom.xml files
* Automation of resolving conflicts
