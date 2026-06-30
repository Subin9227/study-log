from langgraph.graph import StateGraph, END 

from state import EmotionState
from nodes import (
    retrieve_node,
    classify_node,
    map_emotion_node,
    respond_node,
    error_node,
    route_after_classify,
)

def build_graph():
    graph = StateGraph(EmotionState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("classify", classify_node)
    graph.add_node("map_emotion", map_emotion_node)
    graph.add_node("respond", respond_node)
    graph.add_node("error", error_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "classify")
    graph.add_conditional_edges("classify", route_after_classify)
    graph.add_edge("map_emotion", "respond")
    graph.add_edge("respond", END)
    graph.add_edge("error", END)

    return graph.compile()