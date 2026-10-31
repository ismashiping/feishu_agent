"""Register the existing bound nodes and routes without owning research resources."""

from typing import TYPE_CHECKING

from clinical_agent.agents.state import WorkflowState as State

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from clinical_agent.application.research import ResearchService


def build_research_graph(
    service: "ResearchService", *, with_planner: bool
) -> "CompiledStateGraph[State, None, State, State]":
    """Internal assembly seam; ResearchService retains all business operations."""
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(State)
    graph.add_node("retrieve", service._retrieve)
    graph.add_node("prepare", service._prepare)
    graph.add_node("generate", service._generate)
    graph.add_node("validate", service._validate)
    graph.add_node("empty", service._empty)
    graph.add_node("analyze", service._analyze)
    graph.add_node("report", service._report)
    graph.add_node("prior_art", service._prior_agent)
    graph.add_node("design", service._design_agent)
    graph.add_node("feedback", service._feedback)
    graph.add_edge("analyze", "prior_art")
    graph.add_conditional_edges(
        "prior_art",
        lambda state: "design" if state.get("report_requested") else "end",
        {"design": "design", "end": END},
    )
    graph.add_edge("design", "report")
    graph.add_conditional_edges(
        "report",
        lambda state: "end" if state["feedback_target"] == "stop" else "feedback",
        {"feedback": "feedback", "end": END},
    )
    graph.add_conditional_edges(
        "feedback",
        lambda state: state["feedback_target"],
        {"methods": "analyze", "scout": "retrieve"},
    )
    if with_planner:
        graph.add_node("plan", service._plan)
        graph.add_node("clarify", service._clarify)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges(
            "plan", service._plan_route, {"retrieve": "retrieve", "clarify": "clarify"}
        )
        graph.add_conditional_edges(
            "clarify",
            lambda state: "report" if state.get("report_requested") else "end",
            {"report": "report", "end": END},
        )
    else:
        graph.add_edge(START, "retrieve")
    graph.add_conditional_edges(
        "retrieve", service._route, {"empty": "empty", "prepare": "prepare", "analyze": "analyze"}
    )
    graph.add_edge("prepare", "generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", END)
    graph.add_edge("empty", END)
    return graph.compile()
