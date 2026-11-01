"""Compile and inspect both graphs without invoking any external port."""
from clinical_agent.application.research import ResearchService


def main():
    for planner in (None, object()):
        service = ResearchService(retriever=object(), generator=object(), planner=planner)
        graph = service._graph.get_graph()
        print("planner:", planner is not None)
        print("nodes:", sorted(graph.nodes))
        print("edges:", sorted((e.source, e.target, e.conditional) for e in graph.edges))


if __name__ == "__main__":
    main()
