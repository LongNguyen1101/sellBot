import json
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import GraphFunction
from app.core.model import init_model
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage

graph_function = GraphFunction()
llm = init_model()

@tool
def get_qna_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool if user has a question about product such as how to use."""
    try:
        user_input = state["user_input"]
        documents = graph_function.retrieve_qna(user_input)
        tool_response: AgentToolResponse = {}
        
        contents = [
            {
                "id": data["id"],
                "content": data["content"],
                "similarity": data["similarity"]
            } for data in documents
        ]
        
        print(f">>> Contents: {contents}")
        
        tool_response = {
            "status": "finish",
            "content": (
                f"Đây là các tài liệu liên quan: {contents}\n"
                f"Đây là yêu cầu của người dùng: {user_input}\n"
                "Hãy tạo một phản hồi để giải đáp yêu cầu của người dùng "
                "sử dụng các tài liệu liên quan.\n"
                "Ưu tiên tạo phản hồi dựa trên tài liệu liên quan có similarity cao."
                "Lưu ý chỉ trả về 1 câu phản hồi và không giải thích gì thêm.\n"
            )
        }
        
        update = {
            "messages": [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ],
            "status": tool_response["status"]
        }
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)
    
@tool
def get_common_situation_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool if user has problems with products or product is malfuctioning."""
    try:
        user_input = state["user_input"]
        documents = graph_function.retrieve_common_situation(user_input)
        tool_response: AgentToolResponse = {}
        
        contents = [
            {
                "id": data["id"],
                "content": data["content"],
                "similarity": data["similarity"]
            } for data in documents
        ]
        
        print(f">>> Contents: {contents}")
        
        tool_response = {
            "status": "finish",
            "content": (
                f"Đây là các tài liệu liên quan: {contents}\n"
                f"Đây là yêu cầu của người dùng: {user_input}\n"
                "Hãy tạo một phản hồi để giải đáp yêu cầu của người dùng "
                "sử dụng các tài liệu liên quan.\n"
                "Ưu tiên tạo phản hồi dựa trên tài liệu liên quan có similarity cao."
                "Lưu ý chỉ trả về 1 câu phản hồi và không giải thích gì thêm.\n"
            )
        }
        
        update = {
            "messages": [
                ToolMessage
                (
                    content=tool_response["content"],
                    tool_call_id=tool_call_id
                )
            ],
            "status": tool_response["status"]
        }
        
        return Command(
            update=update
        )
        
    except Exception as e:
        raise Exception(e)