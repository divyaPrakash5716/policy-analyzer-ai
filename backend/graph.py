from typing import TypedDict, Literal, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage, trim_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import RedisSaver
import operator
import os
import json
from dotenv import load_dotenv
import redis

# Load env vars - try roots and local
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Initialize LLM
llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0)

# Trimmer for context window management
trimmer = trim_messages(
    max_tokens=4000,
    strategy="last",
    token_counter=llm,
    include_system=True,
    allow_partial=False,
    start_on="human",
)

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    policy_type: str # 'regulatory', 'company', 'both'
    query: str
    documents: List[str] # List of retrieved docs context
    intent: str # 'GREETING', 'POLICY_ANALYSIS', 'POLICY_COMPARISON', 'WEB_SEARCH', 'OFF_TOPIC'
    is_safe: bool
    output_valid: bool
    user_id: str
    long_term_memory: str
    metrics: dict # {'compliance': int, 'risk': str, 'coverage': str, 'table': list}
    alerts: List[str]

def input_guardrail(state: AgentState):
    """
    Checks if the user query is safe and relevant.
    """
    query = state['query']
    guard_prompt = f"""Analyze the following user query for safety and relevance to a Policy Analyzer AI.
Queries should be related to policies, regulations, compliance, greetings, or professional inquiries.
Reject queries that are malicious, promote illegal activities, or are purely nonsensical.

Query: {query}

REPLY WITH 'SAFE' or 'UNSAFE'.
Result:"""
    
    response = llm.invoke([HumanMessage(content=guard_prompt)])
    is_safe = "SAFE" in response.content.upper()
    
    if not is_safe:
        return {"is_safe": False, "messages": [AIMessage(content="I'm sorry, I cannot process this request as it violates safety or relevance guidelines.")]}
    
    return {"is_safe": True}

def load_memory(state: AgentState):
    """
    Retrieves long-term memory from Redis or JSON fallback.
    """
    user_id = state.get('user_id', 'default_user')
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        r.ping()
        memory_key = f"long_term_memory:{user_id}"
        lt_memory = r.get(memory_key)
        if lt_memory:
            return {"long_term_memory": lt_memory.decode('utf-8')}
    except:
        # Fallback to JSON
        LT_MEM_DIR = "long_term_mem"
        mem_path = os.path.join(LT_MEM_DIR, f"{user_id}.json")
        if os.path.exists(mem_path):
            with open(mem_path, "r") as f:
                data = json.load(f)
                return {"long_term_memory": data.get("profile", "No prior history.")}
    
    return {"long_term_memory": "No prior history."}

def monitoring_agent(state: AgentState):
    """
    Proactively scans documents for high-risk clauses and outdated timestamps.
    """
    documents = state.get('documents', [])
    context = "\n".join(documents).lower()
    alerts = []
    
    # 1. High-Risk Clause Detection
    risk_keywords = ["termination without notice", "unlimited liability", "exclusive jurisdiction", "indemnity", "sole discretion"]
    for kw in risk_keywords:
        if kw in context:
            alerts.append(f"HIGH-RISK DETECTED: Found mention of '{kw}' in the policies.")
            
    # 2. Outdated Policy Check (Heuristic)
    # Looking for years like 2020, 2021, 2022 if current year is 2026
    outdated_years = ["2020", "2021", "2022", "2023", "2024"]
    for year in outdated_years:
        if year in context:
            alerts.append(f"OUTDATED POLICY ALERT: This document appears to reference {year} and may be outdated (>1 year).")
            break
            
    return {"alerts": alerts}

def update_memory(state: AgentState):
    """
    Updates long-term memory based on the latest interaction.
    """
    user_id = state.get('user_id', 'default_user')
    last_user_msg = state['query']
    last_ai_msg = state['messages'][-1].content if state['messages'] else "No response"
    current_memory = state.get('long_term_memory', '')
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    summary_prompt = f"""Update the long-term user profile based on the latest interaction.
Existing Profile: {current_memory}
Latest Interaction:
User: {last_user_msg}
AI: {last_ai_msg}

Synthesize a concise, updated profile that captures user preferences, recurring topics, or important context.
Updated Profile:"""
    
    response = llm.invoke([HumanMessage(content=summary_prompt)])
    new_profile = response.content

    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        r.ping()
        memory_key = f"long_term_memory:{user_id}"
        r.set(memory_key, new_profile)
    except:
        # Fallback to JSON file
        LT_MEM_DIR = "long_term_mem"
        os.makedirs(LT_MEM_DIR, exist_ok=True)
        mem_path = os.path.join(LT_MEM_DIR, f"{user_id}.json")
        with open(mem_path, "w") as f:
            json.dump({"profile": new_profile}, f)
    
    return {"long_term_memory": new_profile}

def output_guardrail(state: AgentState):
    """
    Validates the AI's output to ensure it remains grounded in the context.
    """
    if not state.get("documents"):
        return {"output_valid": True}
        
    last_message = state['messages'][-1].content
    context = "\n".join(state['documents'])
    
    guard_prompt = f"""Verify if the following AI response is grounded and supported by the provided context.
Response: {last_message}

Context: {context}

REPLY WITH 'VALID' or 'INVALID'. If it contains hallucinations or info not in context, mark as INVALID.
Result:"""
    
    response = llm.invoke([HumanMessage(content=guard_prompt)])
    output_valid = "VALID" in response.content.upper()
    
    if not output_valid:
        return {"output_valid": False, "messages": [AIMessage(content="[Output Guardrail Triggered] The generated response could not be fully verified against the source documents. Please rephrase or check the original policies.")]}
    
    return {"output_valid": True}

def coordinator(state: AgentState):
    """
    Intelligent Intent Classifier and Guardrail Agent.
    Determines if the query is a greeting, policy-related, or off-topic.
    """
    # Manage context window - trim messages before classification
    trimmed_history = trimmer.invoke(state['messages'])
    query = state['query']
    
    classification_prompt = """You are a highly sophisticated Intent Classifier for a Policy Analyzer AI.
Your task is to classify the user's intent into one of the following categories:

1. **GREETING**: General greetings like "Hi", "Hello", "How are you?", etc.
2. **POLICY_ANALYSIS**: Questions about a single policy (usually Company policy).
3. **POLICY_COMPARISON**: Questions comparing two policies (Regulatory vs Company).
4. **WEB_SEARCH**: General questions about regulations or policy concepts that require external research (e.g., "What is GDPR?").
5. **OFF_TOPIC**: Questions unrelated to policies, regulations, compliance, or greetings (e.g., recipes, coding, general trivia).

REPLY WITH ONLY THE CATEGORY NAME.
Query: {query}
Intent:"""

    response = llm.invoke([HumanMessage(content=classification_prompt.format(query=query))])
    intent = response.content.strip().upper()
    
    # Valid intents check
    valid_intents = ['GREETING', 'POLICY_ANALYSIS', 'POLICY_COMPARISON', 'WEB_SEARCH', 'OFF_TOPIC']
    if intent not in valid_intents:
        # Default to web search or policy analysis if uncertain
        intent = 'POLICY_ANALYSIS'
        
    print(f"DEBUG: Classified Intent -> {intent}")
    return {"intent": intent}

def greeting_agent(state: AgentState):
    """
    Handles general greetings professionally.
    """
    system_prompt = """You are a friendly and professional Policy Analyzer AI assistant.
Respond to the user's greeting warmly and briefy mention that you can help with:
- Analyzing Company Policies
- Comparing Company Policy with Regulatory Requirements
- Researching global regulations (GDPR, ISO, etc.)

Keep the response concise and helpful. Use the conversation history to maintain context if the user continues a greeting."""

    # Trim history and add system prompt
    trimmed_history = trimmer.invoke(state['messages'])
    lt_memory = state.get('long_term_memory', '')
    
    response = llm.invoke([
        SystemMessage(content=f"{system_prompt}\n\nUSER PROFILE (Long-term Context): {lt_memory}")
    ] + trimmed_history)
    return {"messages": [response]}

def guardrail_agent(state: AgentState):
    """
    Handles off-topic queries with a strict refusal, but remains context-aware.
    """
    system_prompt = """You are a Policy Analyzer AI. 
The user has asked something off-topic or unrelated to policy analysis.
Acknowledge the user's message if it's a follow-up (like their name or a casual remark), but pivot back to your core purpose:
- **Policy Analysis**: Understanding specific clauses.
- **Comparison**: Finding gaps between policies and regulations.
- **Research**: Answering questions about global standards (GDPR, ISO, etc.).

Be polite and maintain context from the history, but do not engage in deep off-topic conversation."""

    # Trim history and add system prompt
    trimmed_history = trimmer.invoke(state['messages'])
    lt_memory = state.get('long_term_memory', '')
    
    response = llm.invoke([
        SystemMessage(content=f"{system_prompt}\n\nUSER PROFILE (Long-term Context): {lt_memory}")
    ] + trimmed_history)
    return {"messages": [response]}

def comparator_agent(state: AgentState):
    """
    Agent that compares Regulatory and Company policies with strict guardrails.
    """
    query = state['query']
    context = "\n".join(state.get('documents', []))
    
    system_prompt = f"""You are a Policy Comparator Agent. 
Compare the Company Policy against the Regulatory Policy using the provided context.

## PROVIDED CONTEXT (RAG)
{context}

## YOUR TASK
1. **Analyze** differences and compliance gaps.
2. **Structure** your response with clear Reasoning and Citations.
3. **Generate Metrics**: Provide a Compliance Score (0-100), Risk Level, and Coverage Table.

## RESPONSE FORMAT
- **Reasoning**: Why is the policy compliant/non-compliant?
- **Evidence**: Quote specific clauses (e.g., "Clause 4.2").
- **Metrics JSON**:
```json
{{
  "compliance_score": 85,
  "risk_score": "Medium",
  "coverage_score": "82%",
  "table": [
    {{"Regulation": "GDPR", "Coverage": "82%", "Risk": "Medium"}},
    {{"Regulation": "SOC2", "Coverage": "60%", "Risk": "High"}}
  ]
}}
```

## GUARDRAILS
- ONLY use the provided context.
- DO NOT hallucinate facts."""
    
    # Trim history and add system prompt
    trimmed_history = trimmer.invoke(state['messages'])
    lt_memory = state.get('long_term_memory', '')
    
    response = llm.invoke([
        SystemMessage(content=f"{system_prompt}\n\nUSER PROFILE (Long-term Context): {lt_memory}")
    ] + trimmed_history)
    return {"messages": [response]}

def policy_agent(state: AgentState):
    """
    Agent that analyzes Company Policy with strict guardrails.
    """
    query = state['query']
    context = "\n".join(state.get('documents', []))
    
    system_prompt = f"""You are a Policy Analyst Agent.
Analyze the Company Policy based ONLY on the provided context.

## PROVIDED CONTEXT (RAG)
{context}

## YOUR TASK
- Provide direct answers with structured reasoning.
- Cite specific clauses (e.g., "Yes, termination without notice is allowed only during probation, based on clause 4.2.").

## GUARDRAILS
- ONLY answer about the policy in context.
- NO placeholders or generic info.
- Be proactive if you detect gaps."""

    # Trim history and add system prompt
    trimmed_history = trimmer.invoke(state['messages'])
    lt_memory = state.get('long_term_memory', '')
    
    response = llm.invoke([
        SystemMessage(content=f"{system_prompt}\n\nUSER PROFILE (Long-term Context): {lt_memory}")
    ] + trimmed_history)
    return {"messages": [response]}

def web_agent(state: AgentState):
    """
    Agent that searches the web for policy-related information using Tavily.
    """
    query = state['query']
    
    try:
        search = TavilySearchResults(max_results=3, api_key=os.getenv("TAVILY_API_KEY"))
        results = search.invoke(query)
        context = str(results)
        
        system_prompt = f"""You are a Regulatory Research Agent.
Synthesize the provided web search results to answer the user's query about regulations or standards.

## SEARCH RESULTS
{context}

## GUARDRAILS
- ONLY provide info related to policies, law, or compliance.
- If the search results are irrelevant to the query's core policy intent, inform the user you couldn't find relevant regulatory info.
- Cite sources if available in the results."""
        
        # Trim history and add system prompt
        trimmed_history = trimmer.invoke(state['messages'])
        lt_memory = state.get('long_term_memory', '')

        response = llm.invoke([
            SystemMessage(content=f"{system_prompt}\n\nUSER PROFILE (Long-term Context): {lt_memory}")
        ] + trimmed_history)
        return {"messages": [response]}
    except Exception as e:
        return {"messages": [AIMessage(content=f"I attempted to search for information on this topic, but the search service is currently unavailable. Please try again later or ask about your uploaded policies.")]}

# Graph Construction
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("load_memory", load_memory)
workflow.add_node("monitoring_agent", monitoring_agent)
workflow.add_node("input_guardrail", input_guardrail)
workflow.add_node("coordinator", coordinator)
workflow.add_node("greeting_agent", greeting_agent)
workflow.add_node("guardrail_agent", guardrail_agent)
workflow.add_node("comparator_agent", comparator_agent)
workflow.add_node("policy_agent", policy_agent)
workflow.add_node("web_agent", web_agent)
workflow.add_node("output_guardrail", output_guardrail)
workflow.add_node("update_memory", update_memory)

# Set Entry Point
workflow.set_entry_point("load_memory")

# Edges
workflow.add_edge("load_memory", "monitoring_agent")
workflow.add_edge("monitoring_agent", "input_guardrail")

# Define Routing Logic
def route_after_input(state: AgentState):
    if not state.get("is_safe", True):
        return "update_memory" # Even if unsafe, we update memory context
    return "coordinator"

workflow.add_conditional_edges(
    "input_guardrail",
    route_after_input,
    {
        "coordinator": "coordinator",
        "update_memory": "update_memory"
    }
)

def route_intent(state: AgentState):
    intent = state.get("intent", "OFF_TOPIC")
    if intent == 'GREETING':
        return "greeting"
    elif intent == 'POLICY_ANALYSIS':
        return "policy"
    elif intent == 'POLICY_COMPARISON':
        return "compare"
    elif intent == 'WEB_SEARCH':
        return "web"
    else:
        return "off_topic"

workflow.add_conditional_edges(
    "coordinator",
    route_intent,
    {
        "greeting": "greeting_agent",
        "policy": "policy_agent",
        "compare": "comparator_agent",
        "web": "web_agent",
        "off_topic": "guardrail_agent"
    }
)

# Connect everything to output_guardrail
workflow.add_edge("greeting_agent", "output_guardrail")
workflow.add_edge("guardrail_agent", "output_guardrail")
workflow.add_edge("comparator_agent", "output_guardrail")
workflow.add_edge("policy_agent", "output_guardrail")
workflow.add_edge("web_agent", "output_guardrail")

# Final edges
workflow.add_edge("output_guardrail", "update_memory")
workflow.add_edge("update_memory", END)

# Configure Checkpointer with Redis/In-memory fallback
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    print(f"DEBUG: Attempting to connect to Redis at {REDIS_URL}")
    pool = redis.ConnectionPool.from_url(REDIS_URL, socket_connect_timeout=2)
    r = redis.Redis(connection_pool=pool)
    r.ping()
    memory = RedisSaver(pool)
    print("DEBUG: Using Redis for short-term memory.")
except Exception as e:
    print(f"DEBUG: Redis connection failed ({e}). Falling back to in-memory storage.")
    memory = MemorySaver()

app = workflow.compile(checkpointer=memory)
