import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import pandas as pd  # <--- 新增：引入 pandas 读取表格

# --- 1. Configuration & Setup ---

# 🔐 安全模式：自动从 Streamlit Secrets 读取密钥
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 未找到密钥！请确保配置了 .streamlit/secrets.toml")
    st.stop()

# --- 2. 📂 Load Data & Config (关键修改) ---

# 定义文件路径 (确保文件名完全一致，包括空格)
SERVICES_FILE = "data/iHisto Inc_Product_Service List(20260120).csv"
TOP_LOGO_FILENAME = "images/color_logo-h.png" 
AVATAR_FILENAME = "images/new_logo.png"

# 函数：使用 Pandas 智能读取 CSV 价格表
@st.cache_data  # 加上缓存，提高运行速度
def load_services_from_csv():
    if not os.path.exists(SERVICES_FILE):
        return "⚠️ Service list CSV not found in data folder. Please check file path."
    
    try:
        # --- 修改点在这里 ---
        # 你的图片显示第一行就是标题，所以使用 header=0
        df = pd.read_csv(SERVICES_FILE, header=0)
        
        # 🛡️ 防御性编程：去除列名两端的空格，防止因为 "Sales price " 这种小错误报错
        df.columns = df.columns.str.strip()
        
        service_text = ""
        current_name = ""
        current_desc = ""
        current_price = ""

        # 遍历每一行
        for index, row in df.iterrows():
            # 确保这里引用的列名与你的 Excel/CSV 图片完全一致
            # 图片列名: Product/Service full name | Memo/Description | Sales price
            name = str(row.get('Product/Service full name', '')).strip()
            desc = str(row.get('Memo/Description', '')).strip()
            price = str(row.get('Sales price', '')).strip()

            # 处理 'nan' 字符串 (pandas读取空值时可能会转为 nan)
            if name.lower() == 'nan': name = ""
            if desc.lower() == 'nan': desc = ""
            if price.lower() == 'nan': price = ""

            if name:
                # --- 发现新项目 ---
                # 先保存上一个项目(如果有)
                if current_name:
                    service_text += f"[{current_name}]\n"
                    service_text += f"- Price: ${current_price}\n"
                    if current_desc:
                        service_text += f"- Details: {current_desc}\n"
                    service_text += "\n" # 空行分隔
                
                # 开始记录新项目
                current_name = name
                current_desc = desc
                current_price = price if price else "Inquire"
            else:
                # --- 描述延续行 ---
                # 只有描述，没有名字，说明是上一行的补充
                if current_name and desc:
                    current_desc += f"; {desc}" # 用分号连接补充描述

        # 别忘了保存列表里的最后一项
        if current_name:
            service_text += f"[{current_name}]\n"
            service_text += f"- Price: ${current_price}\n"
            if current_desc:
                service_text += f"- Details: {current_desc}\n"
            service_text += "\n"
            
        return service_text

    except Exception as e:
        return f"Error parsing CSV: {e}"

# 加载服务数据到变量
IHISTO_SERVICES = load_services_from_csv()

# Page Config
st.set_page_config(page_title="iHisto AI Platform", page_icon="🔬", layout="centered")

# CSS Styling
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stChatInput { padding-bottom: 20px; }
        .stChatMessage .stChatMessageAvatar { width: 40px; height: 40px; }
        
        div[data-testid="stPopover"] {
            position: fixed; bottom: 28px; left: 50%; margin-left: -350px;
            width: auto !important; min-width: unset !important; z-index: 99999;
            background-color: transparent !important;
        }
        div[data-testid="stButton"] {
            position: fixed; bottom: 28px; left: 50%; margin-left: 310px;
            width: auto !important; min-width: unset !important; z-index: 99999;
            background-color: transparent !important;
        }
        @media (max-width: 800px) {
            div[data-testid="stPopover"] { left: 10px; bottom: 25px; margin-left: 0; }
            div[data-testid="stButton"] { left: auto; right: 10px; bottom: 25px; margin-left: 0; }
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

# --- 3. Header Section ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists(TOP_LOGO_FILENAME):
        st.image(TOP_LOGO_FILENAME, use_container_width=True) 
    else:
        st.markdown("**iHisto AI Platform**")

    st.markdown(
        "<h3 style='text-align: center; color: #555; margin-top: 10px; font-size: 20px;'>"
        "Advanced Histopathology Scientific Assistant"
        "</h3>", 
        unsafe_allow_html=True
    )
    st.markdown("---")

# --- 4. AI Initialization ---
try:
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# --- 5. Chat Interface Logic ---
INITIAL_MESSAGE = {
    "role": "assistant",
    "content": "Hello! I am the iHisto AI consultant. I can help design experiments, quote prices, and guide your order. How can I assist you today?"
}

if "messages" not in st.session_state:
    st.session_state.messages = [INITIAL_MESSAGE]

for message in st.session_state.messages:
    current_avatar = AVATAR_FILENAME if message["role"] == "assistant" else None
    if current_avatar and not os.path.exists(current_avatar):
        current_avatar = None 
    with st.chat_message(message["role"], avatar=current_avatar):
        st.markdown(message["content"])

# --- 6. Buttons ---
popover = st.popover("➕", help="Upload Image")
with popover:
    st.markdown("### 📂 Upload Image")
    uploaded_file = st.file_uploader("Choose file...", type=["png", "jpg", "jpeg", "tif"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Image Ready!")
        st.image(uploaded_file, width=150)

# New Chat / Reset
if st.button("🔄", help="Start a New Chat"):
    st.session_state.messages = [INITIAL_MESSAGE]
    st.rerun()

if uploaded_file:
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 85px; right: 20px; background-color: #e8f5e9; padding: 8px 15px; border-radius: 10px; border: 1px solid #c8e6c9; z-index: 9998; font-size: 13px;">
            📎 Attached: <b>{uploaded_file.name}</b>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- 7. Processing Logic ---
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
        
        try:
            # --- Vision Mode ---
            if uploaded_file:
                image = Image.open(uploaded_file)
                image_prompt = f"""
                ACT AS: Senior Pathologist for iHisto.
                CONTEXT: User provided an ROI Snapshot.
                USER QUESTION: "{user_input}"
                TASK:
                1. Observe: Morphology & Staining.
                2. Diagnose: Answer concise.
                3. Service: Mention "Digital Pathology Analysis".
                OUTPUT: Short, Concise English.
                """
                response = model.generate_content([image_prompt, image], stream=True)
            
            # --- Text Mode ---
            else:
                text_prompt = f"""
                ACT AS: Senior Scientific Consultant for iHisto.
                
                REFERENCE DATA (iHisto Official Services & Pricing):
                {IHISTO_SERVICES}
                
                YOUR GOAL: Consult, Quote, and Intake.
                
                CURRENT HISTORY:
                {conversation_history}
                
                USER INPUT: "{user_input}"
                
                LOGIC FLOW:
                
                **SCENARIO A: SCIENTIFIC CONSULTATION**
                - Answer questions expertly. Ask Deep Dive technical questions.
                
                **SCENARIO B: PRICING / QUOTE**
                - User asks about cost.
                - ACTION: Use REFERENCE DATA to calculate estimate.
                - Disclaimer: "This is an estimate."
                
                **SCENARIO C: INTAKE (Order)**
                - User says "Ready to order".
                - ACTION: Check Mandatory Fields (Species, Tissue, Fixation, Service, Target).
                - IF ready: Output Summary Table.
                
                OUTPUT: Professional, Concise, Bullet points. English.
                """
                response = model.generate_content(text_prompt, stream=True)

            # --- Stream Output ---
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            st.error(f"Analysis Error: {e}")