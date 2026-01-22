import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import pandas as pd
import re
import json

# --- 1. Configuration & Setup ---
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 未找到密钥！请确保配置了 .streamlit/secrets.toml")
    st.stop()

# --- 2. 📂 Load Data ---
# 确保文件名一致
SERVICES_FILE = "data/iHisto_Inc_Product_Service_List_20260120.csv"
TOP_LOGO_FILENAME = "images/color_logo-h.png" 
AVATAR_FILENAME = "images/new_logo.png"

@st.cache_data
def load_services_from_csv():
    # 路径检查
    if not os.path.exists(SERVICES_FILE):
        return "⚠️ Service list CSV not found in data folder."
    
    try:
        # 读取 CSV，header=0
        df = pd.read_csv(SERVICES_FILE, header=0)
        
        service_text = ""
        current_name = ""
        current_desc = ""
        current_price = ""
        
        for index, row in df.iterrows():
            # 容错获取列名
            col_name = next((c for c in df.columns if "Product" in str(c)), None)
            col_price = next((c for c in df.columns if "Sales" in str(c) or "Price" in str(c)), None)
            col_desc = next((c for c in df.columns if "Memo" in str(c) or "Description" in str(c)), None)
            
            if not col_name: continue

            name = str(row[col_name]).strip()
            price = str(row[col_price]).strip()
            desc = str(row[col_desc]).strip() if col_desc else ""
            
            if name == 'nan': name = ""
            if price == 'nan': price = ""
            
            if name:
                if current_name:
                    # 格式化为 AI 易读的清单格式
                    service_text += f"ITEM: {current_name} | PRICE: ${current_price}\n"
                current_name = name
                current_price = price if price else "Inquire"
            
        if current_name:
            service_text += f"ITEM: {current_name} | PRICE: ${current_price}\n"
            
        return service_text
    except Exception as e:
        return f"Error parsing CSV: {e}"

IHISTO_SERVICES = load_services_from_csv()

# Page Config
st.set_page_config(page_title="iHisto AI Platform", page_icon="🔬", layout="centered")

# CSS Styling (保留您指定的按钮位置)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stChatInput { padding-bottom: 20px; }
        .stChatMessage .stChatMessageAvatar { width: 40px; height: 40px; }
        
        /* === 您的自定义按钮位置 === */
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

        /* 手机端适配 */
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

# --- 4. Init & Session State ---
try:
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# 默认开场白
INITIAL_MESSAGE = {
    "role": "assistant",
    "content": "Welcome to iHisto! To better assist you with your scientific needs, **please let me know your Name, Email, and Organization/Company.**"
}

if "messages" not in st.session_state:
    st.session_state.messages = [INITIAL_MESSAGE]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

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
                    # 🔥🔥🔥 核心修正：强制开启“收据模式” 🔥🔥🔥
                    text_prompt = f"""
                    ACT AS: The iHisto Pricing Calculator (STRICT).
                    
                    OFFICIAL PRICE LIST:
                    {IHISTO_SERVICES}
                    
                    USER QUESTION: "{user_input}"
                    
                    🛑 ABSOLUTE RULES (DO NOT BREAK):
                    1. **ITEMIZE EVERYTHING**: If the user asks for a workflow (e.g., "From tissue to slide"), you MUST list every step.
                    2. **MATH IS MANDATORY**: You must explicitly show the addition.
                       Example: "Processing ($7) + Embedding ($6) + Cutting ($6) + H&E ($6) = Total $25".
                    3. **EXACT PRICES ONLY**: You must copy the exact price from the OFFICIAL PRICE LIST. 
                       - Do not guess. 
                       - Do not round up/down.
                    4. **NO DISCOUNTS**: NEVER invent a discount. Even if the total is high, show the real total.
                    5. **NO RANGES**: Do not say "$50-$100". Calculate the exact sum of the components.
                    
                    BEHAVIOR:
                    - If user asks "How much for H&E?", answer: "Routine Histology:H&E Staining is $6.00".
                    - If user asks for a full slide prep, break it down:
                      1. Processing (Find exact price)
                      2. Embedding (Find exact price)
                      3. Sectioning (Find exact price)
                      4. Staining (Find exact price)
                      5. Total
                    
                    OUTPUT FORMAT: Clear, line-by-line receipt style. English.
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