from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from app.core.state import SellState
from app.core.greeting_nodes import GreetingDialogue
from app.core.router import GraphRouter

def build_graph() -> StateGraph:
    builder = StateGraph(SellState)
    greeting = GreetingDialogue()
    router = GraphRouter()
    
    # Greeting nodes
    builder.add_node("user_input_node", greeting.user_input_node)
    
    # Router
    builder.add_node("check_intent_user_router", router.check_intent_user_router)
    
    
    # Graph
    builder.add_edge(START, "user_input_node")
    builder.add_edge("user_input_node", "check_intent_user_router")
    builder.add_conditional_edges(
        "check_intent_user_router",
        lambda state: state.get("next_node", END),
        {
            "information": END,
            "product": END,
            "qna": END,
            "order": END,
            "update_order": END,
            "other": END,
            END: END
        }
    )
    
    # Set up memory
    memory = MemorySaver()

    # Add
    graph = builder.compile(checkpointer=memory)
    
    return graph