from typing import TypedDict, Literal, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_community.tools.tavily_search import TavilySearchResults
import operator
import os

# Initialize LLM
llm = ChatGroq(model_name="llama3-70b-8192", temperature=0)

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    policy_type: str # 'regulatory', 'company', 'both'
    query: str
    documents: List[str] # List of retrieved docs context

def coordinator(state: AgentState):
    """
    Decides the next step based on policy_type or query intent.
    """
    print(f"Coordinator processing: {state['policy_type']}")
    policy_type = state.get('policy_type')
    
    # Simple routing logic
    if policy_type == 'both':
        return "comparator_agent"
    elif policy_type == 'company':
        return "policy_agent"
    else:
        # If no policy or explicitly general, use web
        return "web_agent"

def comparator_agent(state: AgentState):
    """
    Agent that compares Regulatory and Company policies.
    """
    query = state['query']
    messages = state['messages']
    
    # In a real impl, we would retrieve specific docs here.
    # For now, we assume RAG retrieval happens before or we use the 'documents' in state if populated.
    
    # Prompt for comparison
    system_prompt = "You are a Policy Comparator Agent. Your goal is to compare the Company Policy against the Regulatory Policy. Highlight discrepancies, compliances, and violations."
    
    # augmenting with context (mocked for this step, would call rag_system.get_retriever)
    context = "\n".join(state.get('documents', []))
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Context: {context}\n\nQuery: {query}")])
    return {"messages": [response]}

def policy_agent(state: AgentState):
    """
    Agent that analyzes Company Policy.
    """
    query = state['query']
    
    system_prompt = "You are a Policy Analyst. Answer questions based ONLY on the provided Company Policy."
    context = "\n".join(state.get('documents', []))
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Context: {context}\n\nQuery: {query}")])
    return {"messages": [response]}

def web_agent(state: AgentState):
    """
    Agent that searches the web.
    """
    query = state['query']
    search = TavilySearchResults(max_results=3)
    results = search.invoke(query)
    
    # Synthesize answer
    context = str(results)
    system_prompt = "You are a Web Researcher. Answer the query based on the search results."
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Search Results: {context}\n\nQuery: {query}")])
    return {"messages": [response]}

# Graph Construction
workflow = StateGraph(AgentState)

workflow.add_node("coordinator", coordinator)
workflow.add_node("comparator_agent", comparator_agent)
workflow.add_node("policy_agent", policy_agent)
workflow.add_node("web_agent", web_agent)

workflow.set_entry_point("coordinator")

workflow.add_conditional_edges(
    "coordinator",
    lambda x: x['policy_type'] if x['policy_type'] in ['both', 'company'] else 'web',
    {
        "both": "comparator_agent",
        "company": "policy_agent", 
        "web": "web_agent"
    }
)

workflow.add_edge("comparator_agent", END)
workflow.add_edge("policy_agent", END)
workflow.add_edge("web_agent", END)

app = workflow.compile()
