"""
The LangGraph agent that powers the HCP Log Interaction chat surface.

Role of the agent:
    The rep chats naturally ("Met Dr. Rao today, discussed the new cardiac
    trial, she wants samples sent over, follow up in 2 weeks"). The agent
    is the orchestration layer between that freeform conversation and the
    CRM's structured data model. It decides, turn by turn, whether it has
    enough information to call a tool (log the interaction, pull up the
    HCP's history for context, schedule a follow-up, check compliance, or
    edit a record the rep wants to correct) versus when it should ask a
    clarifying question first. It never lets the rep leave the screen
    without either a saved structured record or an explicit "not yet
    logged" state, so data never silently falls through the cracks.

Graph shape: a standard ReAct loop —
    START -> agent (LLM decides) -> [tools if requested] -> agent -> ... -> END
"""
from typing import Annotated, TypedDict
from sqlalchemy.orm import Session

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools import build_all_tools

SYSTEM_PROMPT = """You are the AI assistant embedded in a pharmaceutical CRM's \
"Log Interaction" screen, helping a field rep record a visit with a \
healthcare professional (HCP) conversationally instead of filling out a form.

Guidelines:
- If the rep references an HCP by name without giving an id, ask for the HCP id \
  (the UI provides an HCP picker so this should rarely happen) or use get_hcp_profile \
  if an hcp_id is already known from context.
- Once you have enough detail about what happened in the visit, call log_interaction \
  with the raw notes so it can be summarized and stored — don't ask the rep to \
  re-type a summary themselves.
- If the rep says something like "actually change that" / "that's wrong" about an \
  interaction that was just logged, call edit_interaction on that interaction_id.
- If the rep mentions sending something later or a next step, call schedule_followup.
- After logging an interaction, proactively call check_compliance on it and mention \
  the result if it raised a flag.
- Keep replies short and conversational. Confirm what was saved in plain language.
"""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_agent(db: Session):
    tools = build_all_tools(db)

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
    ).bind_tools(tools)

    def agent_node(state: AgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_agent(db: Session, messages: list[dict]) -> dict:
    """messages: list of {"role": "user"|"assistant", "content": str}"""
    from langchain_core.messages import HumanMessage, AIMessage

    lc_messages = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        else:
            lc_messages.append(AIMessage(content=m["content"]))

    agent = build_agent(db)
    result = agent.invoke({"messages": lc_messages})

    final_message = result["messages"][-1]
    tool_calls_seen = []
    for m in result["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            tool_calls_seen.extend(
                [{"name": tc["name"], "args": tc["args"]} for tc in m.tool_calls]
            )

    return {
        "reply": final_message.content,
        "tool_calls": tool_calls_seen,
    }
