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
    st.error("⚠️ Key Missing: Please check .streamlit/secrets.toml")
    st.stop()

# --- 2. 📂 核弹级数据加载器 (Nuclear Data Loader) ---
# ❌ 不再使用缓存，强制每次刷新都重读文件
# @st.cache_data  <-- 已注释掉

def find_and_load_csv():
    debug_log = []
    
    # 1. 全盘扫描：寻找所有 CSV 文件
    found_csvs = []
    for root, dirs, files in os.walk("."): # 扫描当前目录及所有子目录
        for file in files:
            if file.endswith(".csv"):
                full_path = os.path.join(root, file)
                found_csvs.append(full_path)
    
    if not found_csvs:
        return None, "❌ CRITICAL ERROR: No .csv files found in the entire project!"

    debug_log.append(f"📂 Found CSVs: {found_csvs}")

    # 2. 智能选择：优先找带 '2026' 的新文件，否则用第一个
    target_file = found_csvs[0]
    for f in found_csvs:
        if "2026" in f:
            target_file = f
            break
    
    debug_log.append(f"👉 Selected Target: {target_file}")

    try:
        # 3. 暴力寻找标题行 (Auto-Header)
        header_row_index = -1
        with open(target_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:30]): # 扫前30行
                if "Product/Service full name" in line:
                    header_row_index = i
                    break
        
        if header_row_index == -1:
            return None, f"❌ Header not found in {target_file}. Content of first 5 lines:\n{lines[:5]}"

        # 4. 读取数据
        df = pd.read_csv(target_file, header=header_row_index)
        
        # 5. 格式化
        service_text = ""
        he_found = False
        he_price = "N/A"
        item_count = 0
        
        current_name = ""
        current_price = ""
        current_desc = ""

        for index, row in df.iterrows():
            name = str(row['Product/Service full name']).strip()
            price = str(row['Sales price']).strip()
            desc = str(row['Memo/Description']).strip()

            if name == 'nan': name = ""
            if price == 'nan': price = ""
            if desc == 'nan': desc = ""

            # H&E 监控
            if "H&E" in name and "Staining" in name:
                he_found = True
                he_price = price

            if name:
                if current_name:
                    service_text += f"ITEM: {current_name} | PRICE: ${current_price}\nDETAILS: {current_desc}\n---\n"
                
                current_name = name
                current_price = price if price else "Inquire"
                current_desc = desc
                item_count += 1
            else:
                if current_name and desc:
                    current_desc += f" {desc}"
        
        if current_name:
            service_text += f"ITEM: {current_name} | PRICE: ${current_price}\nDETAILS: {current_desc}\n---\n"
            item_count += 1
            
        status_msg = f"""
        ✅ File Loaded: {target_file}
        📦 Total Items: {item_count}
        🔬 H&E Status: {'Found' if he_found else 'MISSING'} (Price: ${he_price})
        """
        return service_text, status_msg

    except Exception as e:
        return None, f"❌ Python Exception: {e}"

# 每次刷新页面都会重新执行这里
IHISTO_SERVICES, DEBUG_MSG = find_and_load_csv()

# Page Config (注意标题变化)
st.set_page_config(page_title="iHisto AI (v3.0 Debug)", page_icon="🔬", layout="centered")

# CSS Styling (保持不变)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stChatInput { padding-bottom: 20px; }
        
        /* Desktop Buttons */
        div[data-testid="stPopover"] {
            position: fixed; bottom: 28px; left: 760px; margin-left: 0;
            width: auto !important; min-width: unset !important; z-index: 1000000;
            background-color: transparent !important;
        }
        div[data-testid="stButton"] {
            position: fixed; bottom: 28px; right: 460px; left: auto; margin-left: 0;
            width: auto !important; min-width: unset !important; z-index: 1000000;
            background-color: transparent !important;
        }

        /* Mobile Buttons */
        @media (max-width: 800px) {
            div[data-testid="stPopover"] { left: 5%; bottom: 30px; }
            div[data-testid="stButton"] { right: 5%; left: auto; bottom: 30px; }
        }

        div[data-testid="stPopover"] > button, div[data-testid="stButton"] > button {
            border-radius: 50%; width: 44px; height: 44px; border: 1px solid #ddd;
            background-color: #ffffff; color: #2e86de; font-size: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.2s;
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

INITIAL_MESSAGE = {
    "role": "assistant",
    "content": "Welcome to iHisto! To better assist you with your scientific needs, **please let me know your Name, Email, and Organization/Company.**"
}

if "messages" not in st.session_state:
    st.session_state.messages = [INITIAL_MESSAGE]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

# --- 5. Sidebar ---
with st.sidebar:
    st.title("👤 Client Profile")
    if st.session_state.is_identified:
        st.success("✅ Verified")
        st.text_input("Name", value=st.session_state.client_info["name"], disabled=True)
        st.text_input("Company", value=st.session_state.client_info["company"], disabled=True)
    else:
        st.warning("⏳ Info Pending...")
        st.info("AI features locked.")

    # 🔥🔥 强制显示调试信息 🔥🔥
    st.divider()
    st.markdown("### 🛠️ System Status (Live)")
    if "❌" in DEBUG_MSG:
        st.error(DEBUG_MSG)
    else:
        st.success(DEBUG_MSG) # 这里必须显示 Found: H&E (Price: 6)
        
    if st.button("🗑️ Force Clear Memory"):
        st.cache_data.clear()
        st.rerun()

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
            "content": f"Hi **{user_name}**, I've cleared the chat history. How can I help?"
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
                    RULES: DO NOT invent prices.
                    OUTPUT: Short, Concise English.
                    """
                    response = model.generate_content([image_prompt, image], stream=True)
                else:
                    text_prompt = f"""
                    ACT AS: Senior Scientific Consultant for iHisto.
                    CLIENT INFO: {st.session_state.client_info['name']} from {st.session_state.client_info['company']}.
                    
                    REFERENCE DATA (Official Price List):
                    {IHISTO_SERVICES}
                    
                    YOUR GOAL: Consult, Quote, and Intake.
                    
                    CURRENT HISTORY:
                    {conversation_history}
                    
                    USER INPUT: "{user_input}"
                    
                    🛑 STRICT PRICING RULES (CRITICAL):
                    1. **STRICTLY** use the prices from REFERENCE DATA. 
                    2. **DO NOT INVENT** volume discounts.
                    3. If the list says $6.00, say **$6.00**.
                    
                    OUTPUT: Professional, Concise, Bullet points. English.
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