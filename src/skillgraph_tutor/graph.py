from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ConceptNode:
    name: str
    requires: list[str] = field(default_factory=list)


@dataclass
class ConceptGraph:
    nodes: dict[str, ConceptNode]

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"name": node.name, "requires": sorted(set(node.requires))}
                for node in self.nodes.values()
            ]
        }

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        for node in self.nodes.values():
            if not node.requires:
                lines.append(f"    {slug(node.name)}[{node.name}]")
            for req in node.requires:
                lines.append(f"    {slug(req)}[{req}] --> {slug(node.name)}[{node.name}]")
        return "\n".join(lines)

    def save_json(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")


def parse_syllabus_markdown(markdown: str) -> ConceptGraph:
    headings: list[str] = []
    explicit_requires: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## ") or line.startswith("### "):
            current = line.split(" ", 1)[1].strip()
            headings.append(current)
        elif line.lower().startswith("requires:") and current:
            reqs = [item.strip() for item in line.split(":", 1)[1].split(",") if item.strip()]
            explicit_requires[current] = reqs

    nodes: dict[str, ConceptNode] = {}
    for idx, heading in enumerate(headings):
        if heading in explicit_requires:
            reqs = explicit_requires[heading]
        else:
            reqs = [headings[idx - 1]] if idx > 0 else []
        nodes[heading] = ConceptNode(name=heading, requires=reqs)

    return ConceptGraph(nodes=nodes)


def load_graph(path: str | Path) -> ConceptGraph:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    nodes = {
        item["name"]: ConceptNode(name=item["name"], requires=item.get("requires", []))
        for item in data["nodes"]
    }
    return ConceptGraph(nodes)
