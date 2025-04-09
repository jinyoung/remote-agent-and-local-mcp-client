from typing import Any, Dict, List, Tuple, TypedDict, Annotated, Literal, Optional
import operator
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.tools import BaseTool
from langgraph.prebuilt import create_react_agent


class AgentState(TypedDict):
    """The state of the agent."""
    messages: List[Dict[str, Any]]  # The messages in the conversation
    tools: List[BaseTool]  # The tools available to the agent
    next: Optional[str]  # The next node to route to

def create_agent(tools: List[BaseTool], model: str = "gpt-4o") -> Any:
    """Create an agent that can use tools."""
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are an agent that can help with browser automation and other tasks.
# You have access to the following tools:
# {tool_descriptions}

# Use these tools to help the user.
# """),
#         ("placeholder", "{messages}"),
#     ])
    
    model = ChatOpenAI(model=model, temperature=0)

    agent = create_react_agent(model, tools)
    return agent

def extract_messages(state: AgentState) -> Dict[str, Any]:
    """Extract messages from state and convert to a format suitable for LLM input."""
    return {"messages": state["messages"]}

def extract_tools(state: AgentState) -> Dict[str, Any]:
    """Extract tool descriptions from state for the LLM."""
    tool_descriptions = "\n".join([
        f"- {tool.name}: {tool.description}" for tool in state["tools"]
    ])
    return {"tool_descriptions": tool_descriptions}

# 라우팅 함수 정의
def route_to_next(state: AgentState) -> Literal["tool_executor", "__end__"]:
    """결정하기 - 툴 실행기로 이동할지 종료할지."""
    if state.get("next"):
        return state["next"]
    
    last_message = state["messages"][-1]
    # AIMessage 객체의 속성에 올바르게 접근
    if hasattr(last_message, "content"):
        for tool in state["tools"]:
            if tool.name in last_message.content:
                return "tool_executor"
    return "__end__"

def create_workflow(tools: List[BaseTool]) -> StateGraph:
    """Create a workflow for the agent."""
    # Define a new graph
    builder = StateGraph(AgentState)
    
    # Create an agent that can use tools
    agent = create_agent(tools)
    
    # Tool execution node
    tool_node = ToolNode(tools)
    
    # Add nodes
    builder.add_node("agent", lambda state: agent.invoke({
        **extract_messages(state),
        **extract_tools(state)
    }))
    builder.add_node("tool_executor", tool_node)
    
    # Set the entry point
    builder.set_entry_point("agent")
    
    # Agent -> Tools edge (라우팅 로직 외부로 분리)
    builder.add_conditional_edges(
        "agent",
        route_to_next,
    )
    
    # Tools -> Agent edge
    builder.add_edge("tool_executor", "agent")
    
    # 워크플로우 컴파일
    graph = builder.compile()
    
    return graph

async def run_graph(client_id: str, user_input: str, tools: List[BaseTool]) -> Dict[str, Any]:
    """Run the workflow with the given input."""
    # Initialize the state
    state = AgentState(
        messages=[{"role": "user", "content": user_input}],
        tools=tools,
        next=None
    )
    
    # Create and run the workflow
    graph = create_workflow(tools)
    
    # langgraph 버전 호환성을 위해 여러 실행 메서드 시도
    try:
        # 최신 langgraph API 사용
        result = await graph.ainvoke(state)
        return result
    except Exception as e:
        print(f"Error running graph: {e}")
        raise

