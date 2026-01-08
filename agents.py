from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

class AgentManager:
    def __init__(self, groq_api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.llm = ChatGroq(
            temperature=0, 
            groq_api_key=groq_api_key, 
            model_name=model_name
        )

    def get_web_agent(self):
        search = DuckDuckGoSearchRun()
        
        template = """
        You are a helpful AI assistant. Answer the user's question based on the following web search results.
        If the search results don't contain the answer, say so.
        
        Search Results: {context}
        
        Question: {question}
        
        Answer:
        """
        prompt = PromptTemplate.from_template(template)
        
        chain = (
            {"context": lambda x: search.run(x["question"]), "question": lambda x: x["question"]}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

    def get_policy_agent(self, retriever):
        template = """
        You are a Policy Analyser AI. Answer the question based ONLY on the provided Company Policy context.
        I
        Context: {context}
        
        Question: {question}
        
        Answer:
        """
        prompt = PromptTemplate.from_template(template)
        
        chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

    def get_comparator_agent(self, company_retriever, regulatory_retriever):
        # We need to retrieve from both
        def retrieve_both(query):
            company_docs = company_retriever.invoke(query)
            regulatory_docs = regulatory_retriever.invoke(query)
            return {
                "company_context": "\n".join([d.page_content for d in company_docs]),
                "regulatory_context": "\n".join([d.page_content for d in regulatory_docs])
            }

        template = """
        You are a Comparator Agent. Compare the Company Policy against the Regulatory Policy regarding the user's question.
        Highlight discrepancies, compliances, and missing items.
        
        Company Policy Context:
        {company_context}
        
        Regulatory Policy Context:
        {regulatory_context}
        
        Question: {question}
        
        Analysis:
        """
        prompt = PromptTemplate.from_template(template)
        
        chain = (
            {"context_data": lambda x: retrieve_both(x["question"]), "question": lambda x: x["question"]}
            | RunnablePassthrough.assign(
                company_context=lambda x: x["context_data"]["company_context"],
                regulatory_context=lambda x: x["context_data"]["regulatory_context"]
            )
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

def get_coordinator_response(query: str, session_state, agent_manager: AgentManager):
    # Routing Logic
    has_company = "company_vectorstore" in session_state and session_state["company_vectorstore"] is not None
    has_regulatory = "regulatory_vectorstore" in session_state and session_state["regulatory_vectorstore"] is not None
    
    if has_company and has_regulatory:
        # Comparator
        company_retriever = session_state["company_retriever"]
        regulatory_retriever = session_state["regulatory_retriever"]
        agent = agent_manager.get_comparator_agent(company_retriever, regulatory_retriever)
        return agent.invoke({"question": query})
        
    elif has_company:
        # Policy Agent
        company_retriever = session_state["company_retriever"]
        agent = agent_manager.get_policy_agent(company_retriever)
        return agent.invoke(query)
        
    else:
        # Web Agent
        agent = agent_manager.get_web_agent()
        return agent.invoke({"question": query})
