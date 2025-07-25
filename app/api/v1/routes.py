from fastapi.responses import StreamingResponse
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.graph import build_graph
from app.core.state import init_state
from langchain_core.messages import HumanMessage, AIMessage
from typing import Any
import json


router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    chat_id: str
    user_input: str

@router.get("/")
async def say_hello():
    return {"message": "Hello from FastAPI!"}

@router.post("/chat")
async def chat(request: ChatRequest):
    thread_id = str(request.chat_id)
    config = {"configurable": {"thread_id": thread_id}}

    state = graph.get_state(config).values if graph.get_state(config).values else init_state()
    state["user_input"] = request.user_input
    state["chat_id"] = request.chat_id
    
    events = graph.stream(state, config=config)
    return StreamingResponse(
        stream_messages(events, thread_id),
        media_type="text/event-stream"
    )

async def stream_messages(events: Any, thread_id: str):
    last_printed = None
    
    try:
        for data in events:
            for key, value in data.items():
                    messages = value.get("messages", [])
                    if not messages:
                        continue

                    last_msg = messages[-1]
                    if isinstance(last_msg, AIMessage):
                        content = last_msg.content.strip()
                        if content and content != last_printed:
                            last_printed = content
                            msg = {"content": content}
                            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.01)  # slight delay for smoother streaming
    except Exception as e:
        error_dict = {"error": str(e), "thread_id": thread_id}
        yield f"data: {json.dumps(error_dict, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"