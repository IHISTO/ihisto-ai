import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import pandas as pd
import re
import json

# --- 1. Configuration & Setup ---

# 🔐 安全模式：自动从 Streamlit Secrets 读取密钥
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 未找到密钥！请确保配置了 .streamlit/secrets.toml")
    st.stop()

# --- 2. 📂 Load Data ---
SERVICES_FILE = "data/iHisto Inc_Product_Service List.csv"
TOP_LOGO_FILENAME = "images/color_logo-h.png" 
AVATAR_FILENAME = "images/new_logo.png"

@st.cache_data
def load_services_from_csv():
    if not os.path.exists(SERVICES_FILE):
        return "⚠️ Service list CSV not found in data folder."
    try:
        df = pd.read_csv(SERVICES_FILE, header=2)
        service_text = ""
        current_name = ""
        current_desc = ""
        current_price = ""
        for index, row in df.iterrows():
            name = str(row['Product/Service full name']).strip()
            desc = str(row['Memo/Description']).strip()
            price = str(row['Sales price']).strip()
            if name == 'nan': name = ""
            if desc == 'nan': desc = ""
            if price == 'nan': price = ""
            if name:
                if current_name:
                    service_text += f"[{current_name}]\n- Price: ${current_price}\n"
                    if current_desc: service_text += f"- Details: {current_desc}\n"
                    service_text += "\n"
                current_name = name
                current_desc = desc
                current_price = price if price else "Inquire"
            else:
                if current_name and desc: current_desc += f"\n{desc}"
        if current_name:
            service_text += f"[{current_name}]\n- Price: ${current_price}\n"
            if current_desc: service_text += f"- Details: {current_desc}\n"
            service_text += "\n"
        return service_text
    except Exception as e:
        return f"Error parsing CSV: {e}"

IHISTO_SERVICES = load_services_from_csv()

# Page Config
st.set_page_config(page_title="iHisto AI Platform", page_icon="🔬", layout="centered")

# CSS Styling (最终修复：手机端按比例适配)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stChatInput { padding-bottom: 20px; }
        .stChatMessage .stChatMessageAvatar { width: 40px; height: 40px; }
        
        /* =============================================
           1. 电脑端 (Desktop) - 保持固定在角落
           ============================================= */
        
        /* 左侧 Upload 按钮 (+) */
        div[data-testid="stPopover"] {
            position: fixed; 
            bottom: 28px; 
            left: 760px;  /* 电脑上距离左边 20px */
            margin-left: 0; 
            width: auto !important; 
            min-width: unset !important; 
            z-index: 1000000;
            background-color: transparent !important;
        }
        
        /* 右侧 New Chat 按钮 (🔄) */
        div[data-testid="stButton"] {
            position: fixed; 
            bottom: 28px; 
            right: 460px; /* 电脑上距离右边 20px */
            left: auto;
            margin-left: 0;
            width: auto !important; 
            min-width: unset !important; 
            z-index: 1000000;
            background-color: transparent !important;
        }

        /* =============================================
           2. 手机端 (Mobile) - 按比例缩放 (Proportional)
           ============================================= */
        
        @media (max-width: 800px) {
            /* 左侧 (+) */
            div[data-testid="stPopover"] {
                left: 5%;        /* 【关键】距离左边 5% (按比例) */
                bottom: 85px;    /* 高度：稍微抬高，避开手机输入法 */
                margin-left: 0;
            }
            
            /* 右侧 (🔄) */
            div[data-testid="stButton"] {
                right: 5%;       /* 【关键】距离右边 5% (按比例) */
                left: auto;      /* 必须清除左定位 */
                bottom: 85px;    /* 高度保持一致 */
                margin-left: 0;
            }
        }

        /* =============================================
           3. 按钮美化 (通用)
           ============================================= */
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

# 默认的开场白（用于未识别用户）
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
        st.success("✅ Verified Client")
        st.text_input("Name", value=st.session_state.client_info["name"], disabled=True)
        st.text_input("Email", value=st.session_state.client_info["email"], disabled=True)
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

# --- 7. Buttons (Control Center) ---
popover = st.popover("➕", help="Upload Image")
with popover:
    st.markdown("### 📂 Upload Image")
    uploaded_file = st.file_uploader("Choose file...", type=["png", "jpg", "jpeg", "tif"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Image Ready!")
        st.image(uploaded_file, width=150)

# 🔥 关键修改：智能重置按钮
if st.button("🔄", help="Start a New Chat"):
    # 如果已经识别了身份，只清空聊天，保留身份
    if st.session_state.is_identified:
        user_name = st.session_state.client_info['name']
        st.session_state.messages = [{
            "role": "assistant",
            "content": f"Hi **{user_name}**, I've cleared the chat history for a new topic. \n\nI still have your details on file. How can I help with your next inquiry?"
        }]
        # 注意：这里我们没有重置 client_info
    else:
        # 如果还没识别，就彻底重置
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

    # Memory
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
                    text_prompt = f"""
                    ACT AS: Senior Scientific Consultant for iHisto.
                    CLIENT INFO: {st.session_state.client_info['name']} from {st.session_state.client_info['company']}.
                    REFERENCE DATA (Price List): {IHISTO_SERVICES}
                    YOUR GOAL: Consult, Quote, and Intake.
                    CURRENT HISTORY: {conversation_history}
                    USER INPUT: "{user_input}"
                    LOGIC FLOW:
                    1. Consultation: Expert advice.
                    2. Pricing: Use Reference Data.
                    3. Intake: Verify fields (Species, Tissue, Service, Target).
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