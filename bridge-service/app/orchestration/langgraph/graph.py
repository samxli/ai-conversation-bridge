"""LangGraph ReAct graph: model ↔ tools loop with windowed message history."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.orchestration.langgraph.prompts import (
    MAX_TOOL_LOOP_ITERATIONS,
    MESSAGE_WINDOW_SIZE,
    build_system_prompt,
)


class AgentState(TypedDict):
    """Graph state: conversation messages and tool-loop counter."""

    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int


def build_graph(model, tools: list[BaseTool], checkpointer: BaseCheckpointSaver):
    """Compile the model/tool loop graph with the given checkpointer."""
    model_with_tools = model.bind_tools(tools) if tools else model
    tool_node = ToolNode(tools) if tools else None

    def call_model(state: AgentState) -> dict:
        windowed = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,
            max_tokens=MESSAGE_WINDOW_SIZE,
            start_on="human",
            include_system=True,
            allow_partial=True,
        )
        # Ensure a system prompt is present as the first message for this call.
        sys = SystemMessage(content=build_system_prompt())
        to_model = [sys] + [m for m in windowed if not isinstance(m, SystemMessage)]
        response = model_with_tools.invoke(to_model)
        return {"messages": [response], "iterations": state.get("iterations", 0) + 1}

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        if state.get("iterations", 0) >= MAX_TOOL_LOOP_ITERATIONS:
            return "end"
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "end"

    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    if tool_node is not None:
        builder.add_node("tools", tool_node)
        builder.add_edge(START, "model")
        builder.add_conditional_edges("model", should_continue, {"tools": "tools", "end": END})
        builder.add_edge("tools", "model")
    else:
        builder.add_edge(START, "model")
        builder.add_edge("model", END)

    return builder.compile(checkpointer=checkpointer)


def extract_final_text(messages: list[BaseMessage]) -> str:
    """Return the last AI message text, skipping pure tool-call messages when possible."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            if message.tool_calls and not message.content:
                continue
            content = message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                text = "".join(parts).strip()
                if text:
                    return text
        if isinstance(message, ToolMessage):
            continue
    return ""
