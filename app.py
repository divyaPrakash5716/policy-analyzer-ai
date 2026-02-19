import streamlit as st
import os
import shutil
from rag_engine import DocumentProcessor, VectorDB, HybridRetriever
from agents import AgentManager, get_coordinator_response

# Page Config
st.set_page_config(page_title="Policy Analyser AI", layout="wide")

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = "temp_uploads"
    os.makedirs(st.session_state.temp_dir, exist_ok=True)

# Clean temp dir on start (optional, maybe reset button)

# Sidebar
with st.sidebar:
    st.title("Settings")
    
    # API Key Input
    api_key_input = st.text_input("Groq API Key (required)", type="password")
    if api_key_input:
        st.session_state.groq_api_key = api_key_input
    
    st.markdown("---")
    st.subheader("Document Uploads")
    
    # Company Policy Upload
    company_file = st.file_uploader("Upload Company Policy", type=["pdf"])
    if company_file and "company_processed" not in st.session_state:
        with st.spinner("Processing Company Policy..."):
            # Save to disk
            path = os.path.join(st.session_state.temp_dir, "company_policy.pdf")
            with open(path, "wb") as f:
                f.write(company_file.getbuffer())
            
            # Process
            processor = DocumentProcessor()
            splits = processor.load_and_split(path)
            
            # Vector DB
            vdb = VectorDB()
            vectorstore = vdb.create_vector_store(splits, "company_collection")
            
            # Retriever
            hybrid_retriever = HybridRetriever(splits, vectorstore)
            retriever = hybrid_retriever.get_chain()
            
            # Store in session
            st.session_state.company_retriever = retriever
            st.session_state.company_vectorstore = vectorstore
            st.session_state.company_processed = True
            st.success("Company Policy Processed!")

    # Regulatory Policy Upload
    regulatory_file = st.file_uploader("Upload Regulatory Policy", type=["pdf"])
    if regulatory_file and "regulatory_processed" not in st.session_state:
        with st.spinner("Processing Regulatory Policy..."):
            # Save to disk
            path = os.path.join(st.session_state.temp_dir, "regulatory_policy.pdf")
            with open(path, "wb") as f:
                f.write(regulatory_file.getbuffer())
            
            # Process
            processor = DocumentProcessor()
            splits = processor.load_and_split(path)
            
            # Vector DB - Reuse VDB instance but new collection
            vdb = VectorDB()
            vectorstore = vdb.create_vector_store(splits, "regulatory_collection")
            
            # Retriever
            hybrid_retriever = HybridRetriever(splits, vectorstore)
            retriever = hybrid_retriever.get_chain()
            
            # Store in session
            st.session_state.regulatory_retriever = retriever
            st.session_state.regulatory_vectorstore = vectorstore
            st.session_state.regulatory_processed = True
            st.success("Regulatory Policy Processed!")

    if st.button("Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Main Chat Interface
st.title("Policy Analyser & Comparator AI")

if "groq_api_key" not in st.session_state:
    st.warning("Please enter your Groq API Key in the sidebar to start.")
    st.stop()

# Initialize Manager
agent_manager = AgentManager(st.session_state.groq_api_key)

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ask a question about your policies..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = get_coordinator_response(prompt, st.session_state, agent_manager)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"An error occurred: {e}")
