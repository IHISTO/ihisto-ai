import streamlit as st
import google.generativeai as genai
import os
from PIL import Image

# --- 1. Configuration & Setup ---

# 🔐 安全模式：自动从 Streamlit Secrets 读取密钥
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ 未找到密钥！请确保配置了 .streamlit/secrets.toml")
    st.stop()

# --- 🖼️ 图片配置 ---
TOP_LOGO_FILENAME = "color_logo-h.png"
AVATAR_FILENAME = "new_logo.png"

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
        
        /* --- 1. 左侧悬浮按钮 (➕ Upload) --- */
        div[data-testid="stPopover"] {
            position: fixed;
            bottom: 28px;             
            left: 50%;
            margin-left: -350px;
            width: auto !important;
            min-width: unset !important;
            z-index: 99999;
            background-color: transparent !important;
        }

        /* --- 2. 右侧悬浮按钮 (🔄 New Chat) --- */
        div[data-testid="stButton"] {
            position: fixed;
            bottom: 28px;
            left: 50%;
            margin-left: 310px;
            width: auto !important;
            min-width: unset !important;
            z-index: 99999;
            background-color: transparent !important;
        }

        /* 📱 小屏幕适配 */
        @media (max-width: 800px) {
            div[data-testid="stPopover"] {
                left: 10px;
                bottom: 25px;
                margin-left: 0;
            }
            div[data-testid="stButton"] {
                left: auto;
                right: 10px;
                bottom: 25px;
                margin-left: 0;
            }
        }

        /* --- 3. 按钮通用美化 (圆形) --- */
        
        /* 上传按钮美化 */
        div[data-testid="stPopover"] > button {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            border: 1px solid #ddd;
            background-color: #ffffff; 
            color: #2e86de;
            font-size: 22px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            transition: all 0.2s;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* 新对话按钮美化 (改为蓝色主题) */
        div[data-testid="stButton"] > button {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            border: 1px solid #ddd;
            background-color: #ffffff; 
            color: #2e86de; /* 改回主题蓝 */
            font-size: 20px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            transition: all 0.2s;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* 悬停效果 */
        div[data-testid="stPopover"] > button:hover, 
        div[data-testid="stButton"] > button:hover {
            background-color: #f8f9fa;
            transform: scale(1.1);
            color: #5f27cd; /* 悬停变紫 */
            border-color: #5f27cd;
        }
        
    </style>
""", unsafe_allow_html=True)

# --- 2. Header & Logo Section ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists(TOP_LOGO_FILENAME):
        st.image(TOP_LOGO_FILENAME, use_container_width=True) 
    else:
        st.warning(f"Top Logo '{TOP_LOGO_FILENAME}' not found.")

    st.markdown(
        "<h3 style='text-align: center; color: #555; margin-top: 10px; font-size: 20px;'>"
        "Advanced Histopathology Scientific Assistant"
        "</h3>", 
        unsafe_allow_html=True
    )
    st.markdown("---")

# --- 3. AI Model Initialization ---
try:
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"Connection Failed: {e}")
    st.stop()

# --- 4. Chat Interface Logic ---

# 定义初始问候语
INITIAL_MESSAGE = {
    "role": "assistant",
    "content": "Hello! I am the iHisto AI consultant. How can I help with your research or experiment design today?"
}

# 初始化历史记录
if "messages" not in st.session_state:
    st.session_state.messages = [INITIAL_MESSAGE]

# 显示历史记录
for message in st.session_state.messages:
    current_avatar = AVATAR_FILENAME if message["role"] == "assistant" else None
    if current_avatar and not os.path.exists(current_avatar):
        current_avatar = None 
    with st.chat_message(message["role"], avatar=current_avatar):
        st.markdown(message["content"])

# --- 5. Floating Buttons (The Control Center) ---

# [Left] ➕ Upload Button
popover = st.popover("➕", help="Upload Image")
with popover:
    st.markdown("### 📂 Upload Image")
    uploaded_file = st.file_uploader("Choose file...", type=["png", "jpg", "jpeg", "tif"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Image Ready!")
        st.image(uploaded_file, width=150)

# [Right] 🔄 New Chat Button (关键修改)
# 点击后，不是清空，而是重置为只有初始消息的状态
if st.button("🔄", help="Start a New Chat"):
    st.session_state.messages = [INITIAL_MESSAGE] # 重置为初始状态
    st.rerun() # 立即刷新

# 提示条逻辑
if uploaded_file:
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 85px; right: 20px; background-color: #e8f5e9; padding: 8px 15px; border-radius: 10px; border: 1px solid #c8e6c9; z-index: 9998; font-size: 13px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            📎 Attached: <b>{uploaded_file.name}</b>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- 6. User Input & Processing ---
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
                3. Service: Mention iHisto's "Digital Pathology Services".
                OUTPUT: Short, Concise English.
                """
                response = model.generate_content([image_prompt, image], stream=True)
            
            # --- Text Mode (The "Consult -> Order" Logic) ---
            else:
                text_prompt = f"""
                ACT AS: Senior Scientific Consultant for iHisto.
                
                YOUR GOAL: 
                1. First, discuss science, solve problems, and provide expert advice (Consultation Mode).
                2. ONLY when the user is ready or asks to proceed, switch to "Intake Mode" to fill the "iHisto Request Sheet".
                
                CURRENT HISTORY:
                {conversation_history}
                
                USER INPUT: "{user_input}"
                
                LOGIC FLOW (Follow Strictly):
                
                **SCENARIO A: CONSULTATION (Default)**
                - If the user is asking scientific questions, DO NOT ask about the order form yet.
                - ACTION: Provide a **Short, Concise** expert answer. Ask 1-2 "Deep Dive" technical questions.
                
                **SCENARIO B: TRANSITION TO ORDER**
                - If the user says "That sounds good", "I'm ready", or "Let's do this".
                - ACTION: Ask politely: "**Would you like me to help you submit an order for this experiment now?**"
                
                **SCENARIO C: INTAKE (Form Filling)**
                - ONLY IF the user says "Yes".
                - ACTION: Act as "Intake Manager". Check Mandatory Fields: Species, Tissue, Fixation, Service Type, Target, Analysis.
                - IF fields are missing: Ask for them specifically.
                - IF all fields are present: Output the "Submission Summary" table.
                
                OUTPUT GUIDELINES:
                - Tone: Professional, Expert, Concise.
                - Format: Use Bullet points.
                - Language: Strictly English.
                """
                response = model.generate_content(text_prompt, stream=True)

            # --- 流式输出 ---
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            st.error(f"Analysis Error: {e}")