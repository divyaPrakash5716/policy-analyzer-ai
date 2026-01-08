try:
    import streamlit
    import langchain
    import langchain_groq
    import chromadb
    import sentence_transformers
    import rank_bm25
    import pypdf
    import langchain_community.tools.ddg_search
    print("All imports successful!")
except ImportError as e:
    print(f"Import failed: {e}")
