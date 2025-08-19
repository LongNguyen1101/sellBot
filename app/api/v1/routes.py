from fastapi.responses import StreamingResponse
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.graph import build_graph
from app.core.state import init_state
from langchain_core.messages import AIMessage, HumanMessage
from typing import Any
import json
from app.log.logger_config import setup_logging

logger = setup_logging(__name__)

router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    chat_id: str
    user_input: str
    uuid: str

@router.get("/")
async def say_hello():
    return {"message": "Hello from FastAPI!"}

@router.post("/chat")
async def chat(request: ChatRequest):
    thread_id = str(request.uuid)
    config = {"configurable": {"thread_id": thread_id}}

    state = graph.get_state(config).values if graph.get_state(config).values else init_state()
    state["user_input"] = request.user_input
    state["chat_id"] = request.chat_id
    
    logger.info(f">>>> Process messages: {request.user_input}")
    logger.info(f">>>> Chat id: {request.chat_id} | uuid: {request.uuid}")
    
    events = graph.stream(state, config=config)
    return StreamingResponse(
        stream_messages(events, thread_id),
        media_type="text/event-stream"
    )

# async def stream_messages(events: Any, thread_id: str):
#     last_printed = None
#     closed = False

#     try:
#         async for data in events:
#             for key, value in data.items():
#                 messages = value.get("messages", [])
#                 if not messages:
#                     continue

#                 last_msg = messages[-1]
#                 if isinstance(last_msg, AIMessage):
#                     content = last_msg.content.strip()
#                     if content and content != last_printed:
#                         last_printed = content
#                         msg = {"content": content}
#                         yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
#                         await asyncio.sleep(0.01)
#     except GeneratorExit:
#         closed = True
#         raise
#     except Exception as e:
#         error_dict = {"error": str(e), "thread_id": thread_id}
#         yield f"data: {json.dumps(error_dict, ensure_ascii=False)}\n\n"
#     finally:
#         if not closed:
#             yield "data: [DONE]\n\n"
            
async def stream_messages(events: Any, thread_id: str):
    last_printed = None
    closed = False

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
    except GeneratorExit:
        closed = True
        raise
    except Exception as e:
        error_dict = {"error": str(e), "thread_id": thread_id}
        yield f"data: {json.dumps(error_dict, ensure_ascii=False)}\n\n"
    finally:
        if not closed:
            yield "data: [DONE]\n\n"


