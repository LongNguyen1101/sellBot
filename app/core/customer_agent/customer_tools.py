from operator import add
from langchain_core.tools import tool, InjectedToolCallId
from langsmith import expect
from app.core import graph
from app.core.graph_function import GraphFunction
from app.core.model import init_model
from app.core.state import SellState
from typing import Annotated, List, Literal, LiteralString, Optional, TypedDict
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage


graph_function = GraphFunction()
llm = init_model()

@tool
def find_customer(
    phone_number: Annotated[str, "Phone number of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to find customer in database with phone number"""
    try:
        content = ""
        update = {}
        product_chosen = state["product_chosen"]
        seen_products = state["seen_products"]
        
        customer = graph_function.find_customer_by_phone_number(phone_number)
        if customer is not None:
            content = "Customer found."
            
            update["customer_id"] = customer.customer_id
            update["name"] = customer.name
            update["phone_number"] = customer.phone_number
            update["address"] = customer.address
            
            if product_chosen is None:
                content += (
                    "\nCustomer did not choose product, ask customer to choose."
                    "Here are products which customer recently seen:\n"
                    f"{seen_products}"
                )
                update["next_node"] = "__end__"
            else:
                content += "\nAsk customer whether customer want to add product to cart."
                update["next_node"] = "__end__"
            
        else:
            content = "Customer not found. Ask customer name and address to create order"
            
            update["phone_number"] = phone_number
            update["next_node"] = "__end__"

        update["messages"] = [
            ToolMessage 
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]

        return Command(
            update=update,
        )

    except Exception as e:
        raise Exception(e)

@tool
def register_customer(
    name: Annotated[str, "Name of customer"],
    address: Annotated[str, "Address of customer"],
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool to register a customer"""
    try:
        content = ""
        update = {}
        missing_info = []
        
        if name is None:
            missing_info.append("name")
        if address is None:
            missing_info.append("address")
            
        if len(missing_info) > 0:
            content = f"Missing these information to create customer: {missing_info}"
            update["next_node"] = "__end__"
        else:
        
            phone_number = state["phone_number"]
            customer = graph_function.add_customer(
                name=name,
                address=address,
                phone_number=phone_number
            )

            if customer is not None:
                content = "Create customer successfully. Add product to cart"
                update["name"] = name
                update["address"] = address
                update["customer_id"] = customer.customer_id
                update["next_node"] = "cart_agent"
            else:
                content = "Fail to create customer."
                update["next_node"] = "customer_agent"
        
        update["messages"] = [
            ToolMessage 
            (
                content=content,
                tool_call_id=tool_call_id
            )
        ]

            
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)
    