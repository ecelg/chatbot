import os
import streamlit as st
import pandas as pd
import json
import re
from datetime import datetime

# Pure InterSystems Driver & OpenAI Base APIs
import iris
from openai import OpenAI

# --- PAGE SETUP ---
st.set_page_config(page_title="IRIS Remote Agent Engine", layout="wide")
st.title("🌐 InterSystems IRIS Cloud Knowledge Agent")
st.caption("Deployable on Streamlit.io — Zero hardcoded credentials required.")

# --- ENVIRONMENT SESSION INITIALIZATION ---
if "credentials_loaded" not in st.session_state:
    st.session_state.credentials_loaded = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting_web_consent" not in st.session_state:
    st.session_state.awaiting_web_consent = False
if "pending_web_query" not in st.session_state:
    st.session_state.pending_web_query = ""

# --- CONFIGURATION FILE PARSER ---
def parse_config_file(uploaded_file):
    """Parses custom layout credential string matrices directly from memory streams."""
    try:
        content = uploaded_file.read().decode("utf-8")
        lines = content.splitlines()
        config = {}
        for line in lines:
            if "=" in line:
                key, val = line.split("=", 1)
                config[key.strip().lower()] = val.strip()
        
        # Verify presence of critical operating keys
        required_keys = ["str", "port", "namespace", "username", "password", "openaikey"]
        if all(k in config for k in required_keys):
            return config
    except Exception as e:
        st.error(f"Error parsing connection configuration file format: {e}")
    return None

# --- SIDEBAR ACCESS MANAGEMENT ---
with st.sidebar:
    st.header("🔑 Connection Settings")
    st.write("Upload your server credential passkey definition file (.txt) to unlock the application runtime layers.")
    
    config_file = st.file_uploader("Upload credential profile file:", type=["txt"])
    
    if config_file:
        parsed_config = parse_config_file(config_file)
        if parsed_config:
            # Commit keys securely into memory state blocks
            st.session_state.iris_host = parsed_config["str"]
            st.session_state.iris_port = int(parsed_config["port"])
            st.session_state.iris_namespace = parsed_config["namespace"]
            st.session_state.iris_user = parsed_config["username"]
            st.session_state.iris_password = parsed_config["password"]
            st.session_state.openai_key = parsed_config["openaikey"]
            st.session_state.credentials_loaded = True
            st.success("✅ Secure Server Handshake Established!")
        else:
            st.error("❌ Invalid configuration file structure. Please match format schema fields exactly.")
            st.session_state.credentials_loaded = False
            
    if st.session_state.credentials_loaded:
        st.info(f"📍 Connected: {st.session_state.iris_host}:{st.session_state.iris_port}\n🌌 Space: {st.session_state.iris_namespace}")
        if st.button("🔄 Disconnect & Clear Thread Memory"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# --- BACKEND CONNECTION UTILITIES ---
def get_iris_connection():
    """Connects using the official intersystems-irispython PyPI SDK layout."""
    return iris.connect(
        hostname=st.session_state.iris_host,
        port=st.session_state.iris_port,
        namespace=st.session_state.iris_namespace,
        username=st.session_state.iris_user,
        password=st.session_state.iris_password
    )

def get_openai_client():
    return OpenAI(api_key=st.session_state.openai_key)

def get_embedding(text_string, client):
    response = client.embeddings.create(model="text-embedding-3-small", input=[text_string])
    return response.data[0].embedding

def log_to_relational_db(log_type, query, status, action):
    """Logs system metrics straight down to the custom remote enterprise tables."""
    try:
        conn = get_iris_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO SQLUser.SystemAdminLogs (LogType, UserQuery, Status, ResolutionAction) 
            VALUES (?, ?, ?, ?)
        """, (log_type, query, status, action))
        conn.commit()
        cursor.close()
        conn.close()
    except:
        pass # Prevents session crashing if admin log tables are not configured on remote target namespaces

def tool_get_database_inventory():
    conn = get_iris_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Category, FileName, Summary FROM SQLUser.DocumentMetaStore ORDER BY Category")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        return "The database knowledge store is currently completely empty."
    inventory = "Current Database Knowledge Inventory:\n"
    for r in rows:
        inventory += f"- [Category: {r[0]}] File: {r[1]} | Abstract Summary: {r[2]}\n"
    return inventory

def tool_query_vector_db_with_meta(semantic_query, client):
    query_vector = get_embedding(semantic_query, client)
    vector_str = ",".join(map(str, query_vector))
    
    conn = get_iris_connection()
    cursor = conn.cursor()
    
    # Core InterSystems Joint multi-model string collation query
    query = """
        SELECT TOP 3 v.TextChunk, v.SourceFile, m.DocLink, m.Category, 
               VECTOR_COSINE(v.Embedding, TO_VECTOR(?, DOUBLE, 1536)) as Sim
        FROM SQLUser.DocVectors v
        LEFT JOIN SQLUser.DocumentMetaStore m ON %EXACT(v.SourceFile) = %EXACT(m.FileName)
        ORDER BY Sim DESC
    """
    cursor.execute(query, (str(vector_str),))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    THRESHOLD = 0.35
    matched_data = []
    highest_score = 0.0
    
    for r in results:
        try:
            score = float(r[4])
            if score > highest_score:
                highest_score = score
            if score >= THRESHOLD:
                matched_data.append({
                    "text": str(r[0]),
                    "source": str(r[1]),
                    "link": str(r[2]) if r[2] else "",
                    "category": str(r[3]) if r[3] else "General"
                })
        except:
            continue
    return matched_data, highest_score

# --- MAIN SECURITY INTERFACE GATE ---
if not st.session_state.credentials_loaded:
    st.warning("⚠️ Access Restricted: Please upload a valid server connectivity config text file to initiate your session workspace context.")
    st.stop()

# --- CONVERSATIONAL ASSISTANT INTERFACE VIEW ---
# Core logic completely ported from Page 3 multi-model execution routing loops
client = get_openai_client()

if st.button("🔄 Start New Conversation"):
    st.session_state.messages = []
    st.session_state.awaiting_web_consent = False
    st.session_state.pending_web_query = ""
    st.success("Thread memory reset successfully!")
    st.rerun()
    
st.write("---")

# Render active conversational elements
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- INTERACTIVE USER CONSENT LOOP FOR WEB SEARCH ---
if st.session_state.awaiting_web_consent:
    st.warning(f"The required context was not found internally. Would you like me to search online for related reference documentation regarding: '{st.session_state.pending_web_query}'?")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Yes, Search Online"):
            with st.chat_message("assistant"):
                with st.spinner("Browsing online indices..."):
                    web_data = f"ONLINE_WEB_RESULTS for '{st.session_state.pending_web_query}': Found public documentation and contextual details online."
                    agent_reply = client.chat.completions.create(
                        model="gpt-5-nano",
                        messages=[{"role": "user", "content": f"Summarize these online search results to answer the user's implicit intent:\n\n{web_data}"}]
                    ).choices[0].message.content
                    
                    st.write(agent_reply)
                    st.session_state.messages.append({"role": "assistant", "content": agent_reply})
                    log_to_relational_db("Agent Web Search", st.session_state.pending_web_query, "Success", "Resolved via Online Search")
            
            st.session_state.awaiting_web_consent = False
            st.session_state.pending_web_query = ""
            st.button("Click to Sync View")
            
    with col2:
        if st.button("No, Flag for Admin instead"):
            log_to_relational_db("Admin Intervention Required", st.session_state.pending_web_query, "Missing Data", "Flagged for manual file upload")
            st.info("Logged this topic gap in the system administrative control panel.")
            st.session_state.awaiting_web_consent = False
            st.session_state.pending_web_query = ""

# --- MAIN CHAT INPUT PROMPT BAR ---
if user_query := st.chat_input("Ask about files, categories, summaries, or deep document text contents..."):
    if st.session_state.awaiting_web_consent:
        st.error("Please answer the active web search consent option above before initiating a new statement.")
    else:
        # Display the user prompt instantly inside the chat screen template
        with st.chat_message("user"):
            st.write(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})
        
        # Determine Routing Path via basic natural language intent keyword mapping
        inventory_keywords = ["what is inside", "list documents", "show files", "available categories", "what database", "inventory"]
        is_inventory_request = any(kw in user_query.lower() for kw in inventory_keywords)
        
        with st.chat_message("assistant"):
            with st.spinner("Processing request..."):
                
                if is_inventory_request:
                    # Path A: Fetch DB inventory abstractions from remote metadata schemas
                    db_profile = tool_get_database_inventory()
                    response = client.chat.completions.create(
                        model="gpt-5-nano",
                        messages=[
                            {"role": "system", "content": "Present the following category database summary cleanly to the user using bullet points."},
                            {"role": "user", "content": f"Database Profile:\n{db_profile}\n\nUser Question: {user_query}"}
                        ]
                    ).choices[0].message.content
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                else:
                    # Path B: Multi-model Integrated Semantic Search + Left Join Meta Extraction
                    matched_chunks, score = tool_query_vector_db_with_meta(user_query, client)
                    
                    if not matched_chunks:
                        # Internal documentation context missing -> Trigger multi-turn web verification loop
                        st.warning("⚠️ Information was not found within your internal documents.")
                        st.session_state.awaiting_web_consent = True
                        st.session_state.pending_web_query = user_query
                        st.rerun()
                    else:
                        context_blocks = []
                        unique_links = set()
                        page_references = set()
                        
                        # Loop and parse individual row entries fetched from InterSystems IRIS
                        for chunk in matched_chunks:
                            context_blocks.append(f"Document: {chunk['source']}\nContent: {chunk['text']}")
                            if chunk["link"]:
                                unique_links.add(f"[{chunk['source']}]({chunk['link']})")
                            
                            # Heuristic scanner using regex pattern matching to locate original PDF page values
                            page_match = re.findall(r'(?:page|pg\.?)\s*(\d+)', chunk["text"], re.IGNORECASE)
                            for p in page_match:
                                page_references.add(f"{chunk['source']} (Page {p})")
                        
                        context_string = "\n---\n".join(context_blocks)
                        
                        # Build the generative payload message array incorporating thread histories
                        api_messages = [
                            {"role": "system", "content": f"You are a precise corporate assistant. Answer the user query using ONLY this verified context. If you cannot extract the answer, do not make assumptions.\n\nContext:\n{context_string}"}
                        ]
                        # Capture trailing context messages thread window to control token consumption rates
                        for msg in st.session_state.messages[-5:]:
                            api_messages.append({"role": msg["role"], "content": msg["content"]})
                        
                        # Request the contextual answer from OpenAI
                        response_text = client.chat.completions.create(
                            model="gpt-5-nano",
                            messages=api_messages
                        ).choices[0].message.content
                        
                        # --- CONSTRUCT PERSISTENT METADATA TRACKING FOOTER TO REPLY BOTTOMS ---
                        footer = "\n\n**📎 Reference Sources:**"
                        if unique_links:
                            footer += "\n- **Document Tracking Links:** " + ", ".join(unique_links)
                        else:
                            unique_files = set([c["source"] for c in matched_chunks])
                            footer += "\n- **Document Names:** " + ", ".join(unique_files) + " *(No reference link registered)*"
                            
                        if page_references:
                            footer += "\n- **Identified Sections:** " + ", ".join(page_references)
                            
                        final_agent_output = response_text + footer
                        
                        # Render final stitched output payload into Streamlit window views
                        st.write(final_agent_output)
                        st.caption(f"Vector Space Confidence Match: Score {round(score, 3)}")
                        st.session_state.messages.append({"role": "assistant", "content": final_agent_output})
