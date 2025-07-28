from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from app.core.cart_agent.cart_nodes import CarttNodes
from app.core.customer_agent.customer_nodes import CustomerNodes
from app.core.order_agent.order_nodes import OrderNodes
from app.core.supervisor_agent.supervisor_nodes import SupervisorNodes
from app.core.product_agent.product_nodes import ProductNodes
from app.core.user_agent.user_nodes import UserNodes
from app.core.customer_service_agent.customer_service_nodes import CustomerServiceNodes
from langgraph.pregel import RetryPolicy

from app.core.state import SellState

retry_policy = RetryPolicy(
    max_attempts=2,
    backoff_factor=1,
    retry_on=(Exception,)
)

def build_graph() -> StateGraph:
    supervisor_node = SupervisorNodes()
    product_node = ProductNodes()
    cart_node = CarttNodes()
    user_node = UserNodes()
    order_node = OrderNodes()
    customer_node = CustomerNodes()
    customer_service_node = CustomerServiceNodes()
    builder = StateGraph(SellState)
    
    # builder.add_node("greeting_user_node", user_node.greeting_user_node)
    builder.add_node("user_input_node", user_node.user_input_node)
    builder.add_node("supervisor", supervisor_node.supervisor_agent)
    builder.add_node("product_agent", product_node.product_agent, retry=retry_policy)
    builder.add_node("cart_agent", cart_node.cart_agent, retry=retry_policy)
    builder.add_node("order_agent", order_node.order_agent, retry=retry_policy)
    builder.add_node("customer_agent", customer_node.customer_agent, retry=retry_policy)
    builder.add_node("customer_service_agent", 
                     customer_service_node.customer_service_agent, retry=retry_policy)

    builder.set_entry_point("user_input_node")
    
    # Set up memory
    memory = MemorySaver()

    # Add
    graph = builder.compile(checkpointer=memory)
    
    return graph