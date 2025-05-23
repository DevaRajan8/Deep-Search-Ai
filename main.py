import os
import time
import streamlit as st
from typing import List, Dict
import requests
import json

# Import TavilyClient (optional now)
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

# Graph libraries
import networkx as nx
import graphviz

# ----------------------------------------
# Configuration
# ----------------------------------------
# Tavily API key is provided directly
TAVILY_API_KEY = "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"

# Set Tavily environment variable
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

# Maximum characters to include in context (to avoid 413 errors)
MAX_CONTEXT_LENGTH = 10000  # Adjust based on Groq's limits

# ----------------------------------------
# Groq API helper
# ----------------------------------------
def call_groq_api(prompt: str, max_retries: int = 3) -> str:
    """
    Call Groq API with retry/backoff.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = "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"
    if not api_key:
        st.error("Missing GROQ_API_KEY environment variable.")
        return ""

    # Limit prompt size to prevent 413 errors
    if len(prompt) > MAX_CONTEXT_LENGTH:
        st.warning(f"Trimming context to {MAX_CONTEXT_LENGTH} characters to fit API limits.")
        # Find the last complete sentence before the limit
        cutoff = prompt[:MAX_CONTEXT_LENGTH].rfind('. ') + 1
        if cutoff <= 0:  # If no sentence end found, just cut at the limit
            cutoff = MAX_CONTEXT_LENGTH
        prompt = prompt[:cutoff] + "\n\n[Content truncated due to length...]"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.2
    }
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [])[0].get("message", {}).get("content", "")
        except Exception as e:
            attempt += 1
            st.warning(f"Groq API call failed (attempt {attempt}): {e}")
            
            # If it's still a 413 error, reduce the context further
            if "413" in str(e) and attempt < max_retries:
                new_limit = int(MAX_CONTEXT_LENGTH * 0.75)  # Reduce by 25% each time
                st.warning(f"Further reducing context to {new_limit} characters.")
                cutoff = prompt[:new_limit].rfind('. ') + 1
                if cutoff <= 0:
                    cutoff = new_limit
                prompt = prompt[:cutoff] + "\n\n[Content truncated due to length...]"
                
            time.sleep(2 ** attempt)
    return f"Error: Failed after {max_retries} retries."

# ----------------------------------------
# Research agent using Tavily API directly
# ----------------------------------------
@st.cache_data(show_spinner=True, ttl=600)  # Added TTL for caching
def research_agent(query: str, max_results: int = 5) -> List[Dict]:
    """
    Use Tavily API directly with requests.
    """
    results = []
    response = None  # Initialize response variable
    
    try:
        # Make direct API call to Tavily
        url = "https://api.tavily.com/search"
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {TAVILY_API_KEY}"
        }
        payload = {
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_domains": [],
            "exclude_domains": [],
            "include_answer": True,
            "include_raw_content": True
        }
        
        st.info(f"Sending search request to Tavily for: {query}")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Debug the response
        st.write(f"Received response with status code: {response.status_code}")
        
        # Extract results
        search_results = data.get("results", [])
        if not search_results:
            st.warning("Tavily returned no search results. The API response contains a summary but no individual results.")
            
            # If we have an answer directly from Tavily, create a single synthetic document
            if data.get("answer"):
                results.append({
                    "url": "https://tavily.com/answer",
                    "text": f"Tavily Answer: {data.get('answer')}"
                })
                return results
        
        # Process search results if present
        for result in search_results:
            url = result.get("url", "")
            # First try to get raw_content, fall back to content
            content = result.get("raw_content", result.get("content", ""))
            
            # Check if content exists and is not None
            if content is None:
                content = f"No content available for this result from {url}"
            
            # Limit content length for each source
            if len(content) > MAX_CONTEXT_LENGTH // max_results:
                content = content[:MAX_CONTEXT_LENGTH // max_results] + "... [Content truncated]"
            
            if url:  # Just check if URL exists, content might be empty but that's still valid data
                results.append({"url": url, "text": content})
                
    except Exception as e:
        st.error(f"Tavily search failed: {str(e)}")
        # Debug response
        try:
            if response:
                st.error(f"Response data: {response.text[:500]}...")
        except:
            st.error("Could not access response text")
        
        # Fallback - create a synthetic result with the error
        results.append({
            "url": "error://tavily-search-failed",
            "text": f"Search error: {str(e)}. Please try a different query or check the Tavily API key."
        })
    
    return results

# ----------------------------------------
# Answer drafting agent
# ----------------------------------------
def answer_agent(docs: List[Dict], query: str) -> str:
    if not docs:
        return "No documents found to generate an answer."
    
    # Calculate how many docs we can include based on MAX_CONTEXT_LENGTH
    # Use a more selective approach for choosing context
    total_context_length = 0
    context_parts = []
    
    # Extract first 1000 chars from each doc until we reach our limit
    for doc in docs:
        excerpt = doc['text'][:1000] + "... [truncated]"
        if total_context_length + len(excerpt) <= MAX_CONTEXT_LENGTH - 500:  # Leave room for prompt
            context_parts.append(f"Source: {doc['url']}\n{excerpt}")
            total_context_length += len(excerpt)
        else:
            break
    
    if not context_parts:
        return "The context is empty. Unable to generate an answer."
    
    context = "\n---\n".join(context_parts)
    prompt = (
        "You are a research assistant. Use the following context to answer the question.\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Provide a concise, accurate answer based only on the information in the context. "
        "If the context doesn't contain relevant information, state that clearly."
    )
    return call_groq_api(prompt)

# ----------------------------------------
# Build knowledge graph via networkx + graphviz
# ----------------------------------------
def build_knowledge_graph_dot(docs: List[Dict]) -> graphviz.Digraph:
    dot = graphviz.Digraph()
    
    # Add URL nodes
    for doc in docs:
        key = doc['url']
        # Create shorter label for URLs to improve readability
        short_url = key.split("//")[-1][:30] + "..." if len(key) > 35 else key
        dot.node(key, label=short_url, shape='box')
        
        # Extract capitalized keywords - safely handle content
        text = doc['text']
        if text and not text.startswith("Search error:"):  # Skip error messages
            words = text[:5000].split()  # Limit text analyzed for keywords
            keywords = {w.strip('.,!?():;') for w in words if len(w) > 4 and w[0].isupper() and w.isalpha()}
            
            # Take just the first 5 keywords to keep graph manageable
            for kw in list(keywords)[:5]:
                # Only add if keyword is not just a number
                if not kw.isdigit():
                    dot.node(kw)
                    dot.edge(key, kw)
    return dot

# ----------------------------------------
# Streamlit UI
# ----------------------------------------
def main():
    global MAX_CONTEXT_LENGTH
    st.set_page_config(page_title="Deep Research AI Agentic System", layout="wide")
    st.title("Deep Research AI Agentic System")

    # Input area
    with st.container():
        query = st.text_input("Enter your research query:")
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            max_results = st.slider("Max results to crawl", 1, 10, 3)
        with col2:
            # Create a local variable for context size
            context_size = st.slider("Context size limit", 1000, 15000, MAX_CONTEXT_LENGTH, step=1000)
        with col3:
            run_button = st.button("Run Deep Research", type="primary")
            
    # Add a session state to track API key validation
    
    # Update context size based on slider - this needs to be done here
    MAX_CONTEXT_LENGTH = context_size
    
    if run_button:
        if not query:
            st.error("Enter a query to proceed.")
        else:
            # Create tabs for results
            tab1, tab2, tab3 = st.tabs(["Answer", "Knowledge Graph", "Raw Data"])
            
            with st.spinner("Collecting data via Tavily..."):
                docs = research_agent(query, max_results)
            
            if not docs:
                st.error("No documents found. Try another query.")
            else:
                st.success(f"Collected {len(docs)} documents.")
                
                with st.spinner("Drafting answer via Groq..."):
                    answer = answer_agent(docs, query)
                
                with tab1:
                    st.subheader("Research Answer")
                    st.write(answer)
                    st.download_button(
                        "Download Answer as Text",
                        data=answer,
                        file_name="answer.txt",
                        mime="text/plain"
                    )
                
                with tab2:
                    st.subheader("Knowledge Graph")
                    try:
                        dot = build_knowledge_graph_dot(docs)
                        st.graphviz_chart(dot)
                    except Exception as e:
                        st.error(f"Failed to build knowledge graph: {str(e)}")
                        st.info("The knowledge graph couldn't be generated, possibly due to insufficient keyword extraction from the available content.")
                
                with tab3:
                    st.subheader("Raw Research Data")
                    total_chars = sum(len(doc['text']) for doc in docs)
                    st.info(f"Total content: {total_chars} characters across {len(docs)} documents")
                    
                    for i, doc in enumerate(docs):
                        with st.expander(f"Source {i+1}: {doc['url']} ({len(doc['text'])} chars)"):
                            st.write(doc['text'][:1000] + "..." if len(doc['text']) > 1000 else doc['text'])
                            if not doc['url'].startswith("error://"):
                                st.markdown(f"[Visit source]({doc['url']})")

if __name__ == "__main__":
    main()
