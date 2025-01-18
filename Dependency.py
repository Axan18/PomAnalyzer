class Dependency:
    def __init__(self, group_id, artifact_id, version, scope):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.scope = scope
        self.dependencies = []  # implicit dependencies

    def add_dependency(self, dependency):
        self.dependencies.append(dependency)

    def __repr__(self):
        return f"Dependency({self.group_id}, {self.artifact_id}, {self.version}, {self.scope})"
