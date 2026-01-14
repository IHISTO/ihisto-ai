import streamlit as st
import google.generativeai as genai
import os
from PIL import Image

# --- 1. Configuration & Setup ---

# 🔐 安全模式：自动从 Streamlit Secrets 读取密钥
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # 如果本地没有 secrets，允许临时在这里填，但建议用 secrets.toml
    # INTERNAL_API_KEY = "PASTE_YOUR_KEY_HERE" 
    st.error("⚠️ 未找到密钥！请确保配置了 .streamlit/secrets.toml")
    st.stop()

# --- 🖼️ 图片配置 ---
TOP_LOGO_FILENAME = "color_logo-h.png"
AVATAR_FILENAME = "new_logo.png"

# Page Config: 居中布局
st.set_page_config(page_title="iHisto AI Platform", page_icon="🔬", layout="centered")

# CSS Styling
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .stChatInput { padding-bottom: 20px; }
        .stChatMessage .stChatMessageAvatar { width: 40px; height: 40px; }
        
        /* 悬浮按钮样式 */
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

        @media (max-width: 800px) {
            div[data-testid="stPopover"] {
                left: 10px;
                bottom: 25px;
                margin-left: 0;
            }
        }

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
        
        div[data-testid="stPopover"] > button:hover {
            background-color: #f8f9fa;
            transform: scale(1.1);
            color: #5f27cd;
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
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hello! I am the iHisto AI research consultant. I'm here to help design your experiment. What is your research target or disease model?"
    })

for message in st.session_state.messages:
    current_avatar = AVATAR_FILENAME if message["role"] == "assistant" else None
    if current_avatar and not os.path.exists(current_avatar):
        current_avatar = None 
    with st.chat_message(message["role"], avatar=current_avatar):
        st.markdown(message["content"])

# --- 5. ➕ Upload Button ---
popover = st.popover("➕", help="Upload Image")
with popover:
    st.markdown("### 📂 Upload Image")
    uploaded_file = st.file_uploader("Choose file...", type=["png", "jpg", "jpeg", "tif"], label_visibility="collapsed")
    if uploaded_file:
        st.success("Image Ready!")
        st.image(uploaded_file, width=150)

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

    # --- 关键步骤：构建历史对话记录 (Memory) ---
    # 我们把之前的对话变成一个文本发给 AI，这样它才知道之前聊了什么
    conversation_history = ""
    for msg in st.session_state.messages[-6:]: # 只记最近 6 条，避免太长
        conversation_history += f"{msg['role'].upper()}: {msg['content']}\n"

    chat_avatar = AVATAR_FILENAME if os.path.exists(AVATAR_FILENAME) else None
    
    with st.chat_message("assistant", avatar=chat_avatar):
        message_placeholder = st.empty()
        
        try:
            with st.spinner("iHisto AI is thinking..."):
                # --- Vision Mode ---
                if uploaded_file:
                    image = Image.open(uploaded_file)
                    image_prompt = f"""
                    ACT AS: Senior Pathologist & Scientific Consultant for iHisto.
                    CONTEXT: User provided an image (ROI Snapshot).
                    USER QUESTION: "{user_input}"
                    
                    TASK:
                    1. Observation: Describe morphology/staining.
                    2. Diagnosis: Answer question directly.
                    3. Service: Mention iHisto's "Digital Pathology Services".
                    OUTPUT: Strictly in English.
                    """
                    response = model.generate_content([image_prompt, image])
                
                # --- Text Mode (Consultative Logic) ---
                else:
                    # 🔧 核心修改：顾问式 Prompt
                    text_prompt = f"""
                    ACT AS: Senior Scientific Consultant for iHisto.
                    
                    CURRENT CONVERSATION HISTORY:
                    {conversation_history}
                    
                    USER'S NEW INPUT: "{user_input}"
                    
                    YOUR GOAL: Design a perfect experiment, BUT DO NOT generate the final report immediately unless you have all details.
                    
                    LOGIC FLOW (Follow Strictly):
                    
                    PHASE 1: GREETING & INTENT
                    - If input is "Hello", greet and ask what they are working on.
                    
                    PHASE 2: DISCOVERY (The Interview)
                    - If user mentions a broad topic (e.g., "Lung cancer"), DO NOT write a report yet.
                    - CHECK for missing details: Species (Human/Mouse)? Sample Type (FFPE/Frozen)? Specific Markers?
                    - ACTION: Ask clarifying questions to narrow down the scope.
                    - Example: "Great. To design the best panel, are you working with Human or Mouse tissue? Do you have specific markers in mind?"
                    
                    PHASE 3: CONFIRMATION
                    - If user provides details, summarize them and ASK: "Do you have any other specific requirements, or shall I proceed with the formal proposal?"
                    
                    PHASE 4: REPORT GENERATION (Final Step)
                    - ONLY IF the user says "Go ahead", "Yes", "Create report", or if the conversation history shows all details are clear.
                    - ACTION: Generate the **Formal Scientific Proposal**.
                    - Structure: ### Title, 1. Target Biology, 2. Method Selection, 3. Recommended Antibodies (Cite sources), 4. iHisto Service Link.
                    - No "To/From" headers.
                    
                    OUTPUT: Strictly in English. Professional tone.
                    """
                    response = model.generate_content(text_prompt)

                full_response = response.text
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            st.error(f"Analysis Error: {e}")
