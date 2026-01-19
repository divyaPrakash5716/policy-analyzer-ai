from typing import TypedDict, Literal, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_community.tools.tavily_search import TavilySearchResults
import operator
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize LLM
llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)

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
    # Coordinator doesn't modify state, just routes to next agent
    # Routing is handled by conditional edges
    return {}

def comparator_agent(state: AgentState):
    """
    Agent that compares Regulatory and Company policies.
    """
    query = state['query']
    messages = state['messages']
    
    # In a real impl, we would retrieve specific docs here.
    # For now, we assume RAG retrieval happens before or we use the 'documents' in state if populated.
    
    # Prompt for comparison
    system_prompt = """You are a Policy Comparator Agent specialized in analyzing and comparing regulatory compliance documents.

## YOUR ROLE
Your goal is to compare the Company Policy against the Regulatory Policy. Highlight discrepancies, compliances, and violations.

## SCOPE - ONLY ANSWER QUESTIONS ABOUT:
- Policy comparison and analysis
- Compliance gaps and violations
- Data protection and privacy regulations
- Security requirements and standards
- Individual rights (access, deletion, portability)
- Third-party vendor management
- Cross-border data transfers
- Governance and documentation requirements
- Recommendations for compliance improvement

## WHAT TO AVOID - DO NOT:
- Answer questions unrelated to policy analysis or compliance
- Provide code snippets or programming examples
- Give general knowledge answers outside the policy domain
- Discuss topics like coding, recipes, general trivia, etc.
- Make up information not found in the provided policies

## HANDLING OFF-TOPIC QUERIES
If the user asks something unrelated to policy analysis, respond with:
"I'm a Policy Analyzer AI focused on comparing and analyzing regulatory and company policies. I can help you with:
- Comparing policies for compliance gaps
- Identifying violations and discrepancies  
- Understanding regulatory requirements
- Providing recommendations for compliance

Please ask a question related to the uploaded policies."

## RESPONSE FORMAT
- Use clear headings and bullet points
- Present comparisons in tables when appropriate
- Be specific about which policy (Company vs Regulatory) you're referencing
- Provide actionable recommendations"""
    
    # augmenting with context (mocked for this step, would call rag_system.get_retriever)
    context = "\n".join(state.get('documents', []))
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Context: {context}\n\nQuery: {query}")])
    return {"messages": [response]}

def policy_agent(state: AgentState):
    """
    Agent that analyzes Company Policy.
    """
    query = state['query']
    
    system_prompt = """You are a Policy Analyst Agent specialized in analyzing company policy documents.

## YOUR ROLE
Answer questions based ONLY on the provided Company Policy document. Help users understand their company's data protection practices, security measures, and compliance status.

## SCOPE - ONLY ANSWER QUESTIONS ABOUT:
- Company policy details and requirements
- Data collection and processing practices
- Data retention periods
- Security measures and controls
- Individual rights handling
- Third-party vendor management
- Governance and compliance structure
- Known compliance gaps (if documented)

## WHAT TO AVOID - DO NOT:
- Answer questions unrelated to the company policy
- Provide code snippets or programming examples
- Give general knowledge answers outside the policy domain
- Discuss topics like coding, recipes, general trivia, etc.
- Make up information not found in the provided policy
- Reference regulatory requirements unless comparing

## HANDLING OFF-TOPIC QUERIES
If the user asks something unrelated to policy analysis, respond with:
"I'm a Policy Analyzer AI focused on analyzing company policies. I can help you with:
- Understanding your company's data protection practices
- Explaining security measures and controls
- Clarifying data retention and individual rights procedures
- Identifying documented compliance gaps

Please ask a question related to the uploaded company policy."

## RESPONSE FORMAT
- Use clear headings and bullet points
- Reference specific sections of the policy when possible
- Be factual and stick to what's in the document"""
    context = "\n".join(state.get('documents', []))
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Context: {context}\n\nQuery: {query}")])
    return {"messages": [response]}

def web_agent(state: AgentState):
    """
    Agent that searches the web for policy-related information.
    """
    query = state['query']
    
    # First, check if query is policy-related
    relevance_check_prompt = """You are a query classifier. Determine if the following query is related to:
- Data protection regulations and compliance
- Privacy policies and requirements
- Security standards and frameworks
- Regulatory compliance (GDPR, CCPA, HIPAA, etc.)
- Corporate governance and policy management

Respond with ONLY 'relevant' or 'irrelevant'. Nothing else."""
    
    relevance_response = llm.invoke([SystemMessage(content=relevance_check_prompt), HumanMessage(content=query)])
    
    if 'irrelevant' in relevance_response.content.lower():
        off_topic_response = """I'm a Policy Analyzer AI focused on regulatory compliance and policy analysis. I can only help with questions related to:

- **Data Protection Regulations** (GDPR, CCPA, HIPAA, etc.)
- **Privacy Policies** and compliance requirements
- **Security Standards** and frameworks
- **Corporate Governance** and policy management
- **Compliance Gap Analysis** and recommendations

Your question appears to be outside my scope. Please ask something related to policy analysis or regulatory compliance."""
        
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=off_topic_response)]}
    
    try:
        search = TavilySearchResults(max_results=3, api_key=os.getenv("TAVILY_API_KEY"))
        results = search.invoke(query)
        
        # Synthesize answer
        context = str(results)
        system_prompt = """You are a Regulatory Research Agent specialized in policy and compliance topics.

## YOUR ROLE
Search and synthesize information about data protection regulations, privacy laws, security standards, and compliance frameworks.

## SCOPE - ONLY PROVIDE INFORMATION ABOUT:
- Data protection regulations (GDPR, CCPA, HIPAA, PCI-DSS, etc.)
- Privacy laws and requirements
- Security standards and frameworks (ISO 27001, SOC 2, NIST, etc.)
- Compliance best practices
- Regulatory updates and changes
- Industry-specific compliance requirements

## WHAT TO AVOID - DO NOT:
- Answer questions unrelated to policy/compliance/regulations
- Provide code snippets or programming examples
- Give general knowledge answers outside the regulatory domain
- Discuss topics like coding, recipes, general trivia, etc.

## RESPONSE FORMAT
- Cite sources when possible
- Use clear headings and bullet points
- Focus on actionable compliance information"""
        
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Search Results: {context}\n\nQuery: {query}")])
        return {"messages": [response]}
    except Exception as e:
        # Fallback response if web search fails
        error_message = f"Web search is currently unavailable. Error: {str(e)}"
        fallback_prompt = """You are a Policy Analyzer AI. Web search is unavailable. 
Politely inform the user that you cannot search the web right now, but you can help with:
- Analyzing uploaded policies
- Comparing regulatory vs company policies
- Identifying compliance gaps

Do NOT answer off-topic questions. Stay focused on policy analysis."""
        response = llm.invoke([SystemMessage(content=fallback_prompt), HumanMessage(content=f"The user asked: {query}")])
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
    lambda x: "both" if x['policy_type'] == 'both' else ("company" if x['policy_type'] == 'company' else "web"),
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
