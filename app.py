import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import pandas as pd
import re
import json
import glob

# --- 1. Configuration & Setup ---
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Key Missing. Please check .streamlit/secrets.toml")
    st.stop()

TOP_LOGO_FILENAME = "images/color_logo-h.png" 
AVATAR_FILENAME = "images/new_logo.png"

# --- 2. 📂 "Universal" Data Loader (核心引擎) ---
@st.cache_data
def load_services_universal():
    # 扫描所有 CSV
    possible_files = glob.glob("*.csv") + glob.glob("data/*.csv")
    
    if not possible_files:
        return "⚠️ System Error: No Price List Found.", None

    found_df = None
    
    # 循环尝试读取
    for f in possible_files:
        # 尝试多种编码
        encodings_to_try = ['utf-8', 'ISO-8859-1', 'cp1252', 'gbk']
        for encoding in encodings_to_try:
            try:
                df = pd.read_csv(f, header=0, encoding=encoding)
                df.columns = df.columns.str.strip()
                
                # 检查是否包含关键列
                col_name = next((c for c in df.columns if 'product' in c.lower() or 'service' in c.lower()), None)
                col_price = next((c for c in df.columns if 'price' in c.lower() or 'sales' in c.lower()), None)
                
                if col_name and col_price:
                    found_df = df
                    break 
            except:
                continue
        if found_df is not None:
            break

    if found_df is None:
        return "⚠️ Error: Price list format incorrect.", None

    # 格式化数据给 AI
    try:
        service_text = ""
        col_name = next((c for c in found_df.columns if 'product' in c.lower() or 'service' in c.lower()), None)
        col_price = next((c for c in found_df.columns if 'price' in c.lower() or 'sales' in c.lower()), None)
        col_desc = next((c for c in found_df.columns if 'memo' in c.lower() or 'desc' in c.lower()), None)
        
        current_name = ""
        current_desc = ""
        current_price = ""
        
        for index, row in found_df.iterrows():
            name = str(row[col_name]).strip()
            raw_price = str(row[col_price]).strip()
            price = raw_price.replace(',', '').replace('"', '') # 清洗价格
            desc = str(row[col_desc]).strip() if col_desc and pd.notna(row[col_desc]) else ""

            if name == 'nan': name = ""
            if price == 'nan': price = ""
            
            if name:
                if current_name:
                    service_text += f"ITEM: {current_name} | PRICE: ${current_price}\n"
                    if current_desc: service_text += f"DETAILS: {current_desc}\n"
                    service_text += "---\n"
                current_name = name
                current_price = price if price else "Inquire"
                current_desc = desc
            else:
                if current_name and desc: current_desc += f" {desc}"
        
        if current_name:
            service_text += f"ITEM: {current_name} | PRICE: ${current_price}\n"
        
        return service_text, found_df

    except Exception:
        return "⚠️ Error processing data.", None

# 加载数据
IHISTO_SERVICES, _ = load_services_universal()

# Page Config
st.set_page_config(page_title="iHisto AI Platform", page_icon="🔬", layout="centered")

# CSS Styling (保持 -200px / 450px)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stChatInput { padding-bottom: 20px; }
        .stChatMessage .stChatMessageAvatar { width: 40px; height: 40px; }
        
        div[data-testid="stPopover"] {
            position: fixed; bottom: 28px; left: 50%; margin-left: -200px;
            width: auto !important; min-width: unset !important; z-index: 1000000;
            background-color: transparent !important;
        }
        div[data-testid="stButton"] {
            position: fixed; bottom: 28px; left: 50%; margin-left: 450px;
            width: auto !important; min-width: unset !important; z-index: 1000000;
            background-color: transparent !important;
        }
        @media (max-width: 800px) {
            div[data-testid="stPopover"] { left: 10px; bottom: 80px; margin-left: 0; }
            div[data-testid="stButton"] { left: auto; right: 10px; bottom: 80px; margin-left: 0; }
        }
        div[data-testid="stPopover"] > button, div[data-testid="stButton"] > button {
            border-radius: 50%; width: 40px; height: 40px; border: 1px solid #ddd;
            background-color: #ffffff; color: #2e86de; font-size: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08); transition: all 0.2s;
            display: flex; align-items: center; justify-content: center;
        }
        div[data-testid="stPopover"] > button:hover, div[data-testid="stButton"] > button:hover {
            background-color: #f8f9fa; transform: scale(1.1); color: #5f27cd; border-color: #5f27cd;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. Header ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists(TOP_LOGO_FILENAME):
        st.image(TOP_LOGO_FILENAME, use_container_width=True) 
    else:
        st.markdown("**iHisto AI Platform**")
    st.markdown("<h3 style='text-align: center; color: #555; margin-top: 10px; font-size: 20px;'>Advanced Histopathology Scientific Assistant</h3>", unsafe_allow_html=True)
    st.markdown("---")

# --- 4. Init & Session ---
try:
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

INITIAL_MESSAGE = {
    "role": "assistant",
    "content": "Welcome to iHisto! To better assist you with your scientific needs, **please let me know your Name, Email, and Organization/Company.**"
}

if "messages" not in st.session_state:
    st.session_state.messages = [INITIAL_MESSAGE]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

# --- 5. Sidebar (Clean Version) ---
with st.sidebar:
    st.title("👤 Client Profile")
    if st.session_state.is_identified:
        st.success("✅ Verified Client")
        st.text_input("Name", value=st.session_state.client_info["name"], disabled=True)
        st.text_input("Company", value=st.session_state.client_info["company"], disabled=True)
    else:
        st.warning("⏳ Info Pending...")
        st.text_input("Name (Draft)", value=st.session_state.client_info["name"] or "", disabled=True)
        st.text_input("Email (Draft)", value=st.session_state.client_info["email"] or "", disabled=True)
        st.text_input("Company (Draft)", value=st.session_state.client_info["company"] or "", disabled=True)
        st.info("AI features locked.")

# --- 6. Chat Display ---
for message in st.session_state.messages:
    current_avatar = AVATAR_FILENAME if message["role"] == "assistant" else None
    if current_avatar and not os.path.exists(current_avatar): current_avatar = None 
    with st.chat_message(message["role"], avatar=current_avatar):
        st.markdown(message["content"])

# --- 7. Buttons ---
popover = st.popover("➕", help="Upload Image")
with popover:
    st.markdown("### 📂 Upload Image")
    uploaded_file = st.file_uploader("Choose file...", type=["png", "jpg", "jpeg", "tif"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Image Ready!")
        st.image(uploaded_file, width=150)

if st.button("🔄", help="Start a New Chat"):
    if st.session_state.is_identified:
        user_name = st.session_state.client_info['name']
        st.session_state.messages = [{
            "role": "assistant",
            "content": f"Hi **{user_name}**, I've cleared the chat history. How can I help you?"
        }]
    else:
        st.session_state.messages = [INITIAL_MESSAGE]
        st.session_state.client_info = {"name": None, "email": None, "company": None}
        st.session_state.is_identified = False
    st.rerun()

if uploaded_file:
    st.markdown(f"<div style='position: fixed; bottom: 85px; right: 20px; background-color: #e8f5e9; padding: 8px 15px; border-radius: 10px; border: 1px solid #c8e6c9; z-index: 9998; font-size: 13px;'>📎 Attached: <b>{uploaded_file.name}</b></div>", unsafe_allow_html=True)

# --- 8. Logic Controller ---
user_input = st.chat_input("Chat with iHisto AI...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    conversation_history = ""
    for msg in st.session_state.messages[-12:]: 
        conversation_history += f"{msg['role'].upper()}: {msg['content']}\n"

    chat_avatar = AVATAR_FILENAME if os.path.exists(AVATAR_FILENAME) else None
    
    with st.chat_message("assistant", avatar=chat_avatar):
        message_placeholder = st.empty()
        full_response = ""
        
        # --- Gatekeeper ---
        if not st.session_state.is_identified:
            try:
                current_info_str = json.dumps(st.session_state.client_info)
                gatekeeper_prompt = f"""
                You are the iHisto Receptionist.
                GOAL: Complete the Client Profile (Name, Email, Company).
                CURRENT KNOWN INFO (JSON): {current_info_str}
                USER INPUT: "{user_input}"
                INSTRUCTIONS:
                1. Update JSON with new info.
                2. OUTPUT: ###DATA: {{...}}### then a polite response.
                """
                response = model.generate_content(gatekeeper_prompt)
                response_text = response.text
                match = re.search(r'###DATA: ({.*?})###', response_text)
                clean_reply = re.sub(r'###DATA: {.*?}###', '', response_text).strip()
                
                if match:
                    new_data = json.loads(match.group(1))
                    st.session_state.client_info = new_data
                    if new_data.get("name") and new_data.get("email") and new_data.get("company"):
                        st.session_state.is_identified = True 
                        welcome_back_msg = f"Thank you, **{new_data['name']}** from **{new_data['company']}**. Verification successful! ✅\n\nI can now assist you with experimental design, pricing, or submitting an order. How can I help you?"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_back_msg})
                        st.rerun()
                    else:
                        message_placeholder.markdown(clean_reply)
                        st.session_state.messages.append({"role": "assistant", "content": clean_reply})
                else:
                    message_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Receptionist Error: {e}")

        # --- Unlocked Mode ---
        else:
            try:
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    image_prompt = f"""
                    ACT AS: Senior Pathologist for iHisto.
                    CLIENT: {st.session_state.client_info['name']} ({st.session_state.client_info['company']}).
                    CONTEXT: User provided an ROI Snapshot.
                    USER QUESTION: "{user_input}"
                    TASK: Diagnose and Mention "Digital Pathology Analysis".
                    OUTPUT: Short, Concise English.
                    """
                    response = model.generate_content([image_prompt, image], stream=True)
                else:
                    # 🔥 双阶段智能 Prompt：防止在信息不足时瞎报价 🔥
                    text_prompt = f"""
                    ACT AS: Senior Scientific Consultant for iHisto.
                    
                    OFFICIAL PRICE DATA (Source of Truth): 
                    {IHISTO_SERVICES}
                    
                    USER INPUT: "{user_input}"
                    
                    YOUR GOAL: Guide the user to a solution, but ONLY quote when details are clear.
                    
                    🛑 LOGIC FLOW (MANDATORY):
                    
                    **PHASE 1: ANALYZE THE REQUEST**
                    - Is the request VAGUE? (e.g., "tumor study", "IHC service", "how much is scanning")
                    - Is the request SPECIFIC? (e.g., "H&E for 10 mouse lung slides", "CD3 IHC on 5 slides")
                    
                    **PHASE 2: EXECUTE**
                    
                    ► IF VAGUE (Consultation Mode):
                      - DO NOT generate a price receipt yet.
                      - ASK clarifying questions (e.g., "What species?", "Which markers?", "How many samples?", "Do you need analysis?").
                      - Provide general scientific advice relevant to the topic.
                    
                    ► IF SPECIFIC (Quote Mode):
                      - Provide Scientific Workflow advice.
                      - GENERATE "STRICT PRICING RECEIPT":
                        1. USE EXACT PRICES from data.
                        2. SHOW MATH: List components and ADD them up (e.g. $7 + $6 = $13).
                        3. NO DISCOUNTS.
                    
                    OUTPUT: Professional, conversational, expert tone. English.
                    """
                    response = model.generate_content(text_prompt, stream=True)

                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
            except Exception as e:
                st.error(f"Analysis Error: {e}")
