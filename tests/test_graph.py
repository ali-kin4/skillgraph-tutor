from skillgraph_tutor.graph import parse_syllabus_markdown


def test_parse_syllabus_and_requires():
    markdown = """
## A
## B
requires: A
## C
"""
    graph = parse_syllabus_markdown(markdown)
    assert "A" in graph.nodes
    assert graph.nodes["B"].requires == ["A"]
    assert graph.nodes["C"].requires == ["B"]
