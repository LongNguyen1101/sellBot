import json
from app.core.utils.class_parser import AgentToolResponse
from app.core.utils.graph_function import graph_function
from typing import Annotated
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from app.core.state import SellState
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from app.db.database import session_scope
from app.services.crud_public import PublicCRUD
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

@tool
def get_qna_tool(
    state: Annotated[SellState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Use this tool if user has a question about product such as how to use."""
    try:
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            user_input = state["user_input"]
            current_task = state["current_task"]
            documents = graph_function.retrieve_qna(public_crud=public_crud, user_input=current_task)
            tool_response: AgentToolResponse = {}
            
            contents = [
                {
                    "id": data["id"],
                    "content": data["content"],
                    "similarity": data["similarity"]
                } for data in documents
            ]
            
            logger.info(f"Nội dung qna trả về: {contents}")
            
            tool_response = {
                "status": "finish",
                "content": (
                    f"Đây là các tài liệu liên quan: {contents}\n"
                    f"Đây là yêu cầu của người dùng: {user_input}\n"
                    f"Yêu cầu hiện tại của hệ thống: {current_task}.\n"
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
        with session_scope() as db_session:
            public_crud = PublicCRUD(db_session)
            user_input = state["user_input"]
            current_task = state["current_task"]
            documents = graph_function.retrieve_common_situation(
                public_crud=public_crud, 
                user_input=user_input
            )
            tool_response: AgentToolResponse = {}
            
            contents = [
                {
                    "id": data["id"],
                    "content": data["content"],
                    "similarity": data["similarity"]
                } for data in documents
            ]
            
            logger.info(f"Nội dung common_situations trả về: {contents}")
            
            tool_response = {
                "status": "finish",
                "content": (
                    f"Đây là các tài liệu liên quan: {contents}\n"
                    f"Đây là yêu cầu của người dùng: {user_input}.\n"
                    f"Yêu cầu hiện tại của hệ thống: {current_task}.\n"
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
