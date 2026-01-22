import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import json
import re
from PIL import Image

# --- 1. 配置与密钥 ---
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    st.error("⚠️ Key Missing. Please check .streamlit/secrets.toml")
    st.stop()

# --- 2. 核心：智能数据读取 (Smart Loader) ---
DATA_DIRS = ["data", "."] 
# 两个文件名都列在这里，确保能找到
TARGET_FILENAME = "iHisto Inc_Product_Service List(20260120).csv"
BACKUP_FILENAME = "iHisto Inc_Product_Service List.csv"

@st.cache_data(show_spinner=False)
def load_data_final():
    logs = []
    found_path = None
    
    # [Step 1] 定位文件
    for d in DATA_DIRS:
        if os.path.exists(d):
            files = os.listdir(d)
            if TARGET_FILENAME in files:
                found_path = os.path.join(d, TARGET_FILENAME)
                break 
            elif BACKUP_FILENAME in files and found_path is None:
                found_path = os.path.join(d, BACKUP_FILENAME)
    
    if not found_path:
        return None, ["❌ Fatal: CSV file not found."], 0

    # [Step 2] 读取内容
    try:
        # 智能探测：标题在哪一行？
        header_idx = 0
        with open(found_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:20]):
                if "Product/Service full name" in line:
                    header_idx = i
                    break
        
        df = pd.read_csv(found_path, header=header_idx)
        
        # [Step 3] 解析全部数据
        service_text = ""
        count = 0
        
        # 遍历表格的每一行
        for index, row in df.iterrows():
            name = str(row['Product/Service full name']).strip()
            price = str(row['Sales price']).strip()
            desc = str(row['Memo/Description']).strip()

            if name == 'nan': name = ""
            if price == 'nan': price = ""
            if desc == 'nan': desc = ""

            # 只要名字不为空，就加入到 AI 的知识库中
            if name:
                service_text += f"ITEM: {name} | PRICE: ${price}\nDETAILS: {desc}\n---\n"
                count += 1
                
        logs.append(f"📂 Loaded: {found_path}")
        return service_text, logs, count

    except Exception as e:
        return None, [f"❌ Error: {e}"], 0

# 加载数据
IHISTO_SERVICES, DEBUG_LOGS, TOTAL_COUNT = load_data_final()

# --- 3. 页面设置 ---
st.set_page_config(page_title="iHisto AI", page_icon="🔬")

# 自定义 CSS
st.markdown("""
    <style>
        div[data-testid="stPopover"] { position: fixed; bottom: 28px; left: 760px; z-index: 999; }
        div[data-testid="stButton"] { position: fixed; bottom: 28px; right: 460px; z-index: 999; }
        @media (max-width: 800px) {
            div[data-testid="stPopover"] { left: 5%; bottom: 30px; }
            div[data-testid="stButton"] { right: 5%; bottom: 30px; }
        }
        div[data-testid="stPopover"] > button, div[data-testid="stButton"] > button {
            border-radius: 50%; width: 44px; height: 44px; border: 1px solid #ddd;
            background-color: white; color: #2e86de; font-size: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# --- 4. 侧边栏 (全量数据监控) ---
with st.sidebar:
    st.title("🛡️ System Status")
    
    if TOTAL_COUNT > 0:
        st.success(f"System Ready")
        st.info(f"📦 Total Services Loaded: {TOTAL_COUNT}")
        
        # 🔥 这里可以让您看到所有被读取的服务
        with st.expander("📜 Check All Services List"):
            st.text(IHISTO_SERVICES)
    else:
        st.error("❌ No Data Loaded")
        for log in DEBUG_LOGS:
            st.text(log)
    
    if st.button("🧹 Refresh System"):
        st.cache_data.clear()
        st.rerun()

# --- 5. 主界面逻辑 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("images/color_logo-h.png"):
        st.image("images/color_logo-h.png", use_container_width=True)
    else:
        st.markdown("### iHisto AI Platform")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome! Please verify your Name, Email, and Company."}]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

for msg in st.session_state.messages:
    avatar = "images/new_logo.png" if msg["role"] == "assistant" and os.path.exists("images/new_logo.png") else None
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

popover = st.popover("➕")
with popover:
    st.markdown("### Upload Image")
    uploaded_file = st.file_uploader("File", label_visibility="collapsed")
    if uploaded_file: st.success("Uploaded!")

if st.button("🔄"):
    if st.session_state.is_identified:
         st.session_state.messages = [{"role": "assistant", "content": f"Hi {st.session_state.client_info['name']}, chat cleared."}]
    else:
         st.session_state.messages = [{"role": "assistant", "content": "Welcome! Please verify Name, Email, Company."}]
         st.session_state.client_info = {"name": None, "email": None, "company": None}
         st.session_state.is_identified = False
    st.rerun()

user_input = st.chat_input("How can I help you?")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    if not st.session_state.is_identified:
        try:
            info_str = json.dumps(st.session_state.client_info)
            resp = model.generate_content(f"Extract Name,Email,Company from '{user_input}'. Current info: {info_str}. Return JSON only: ###DATA: {{...}}###")
            match = re.search(r'###DATA: ({.*?})###', resp.text)
            if match:
                data = json.loads(match.group(1))
                st.session_state.client_info = data
                if all(data.values()):
                    st.session_state.is_identified = True
                    st.session_state.messages.append({"role": "assistant", "content": f"Thanks {data['name']}! You are verified. ✅"})
                    st.rerun()
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "I still need your full details (Name, Email, Company)."})
            else:
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
        except: st.error("Verification Error")
    
    else:
        # 🔥 通用版 Prompt：不再只盯着 H&E
        prompt = f"""
        ACT AS: iHisto Scientific Consultant.
        
        OFFICIAL PRICE DATA (Full Database):
        {IHISTO_SERVICES}
        
        USER QUERY: "{user_input}"
        
        RULES:
        1. Search the ENTIRE PRICE DATA for the service requested by the user.
        2. Use the EXACT price listed in the data.
        3. If the service is not found, verify if it might be under a slightly different name.
        4. No volume discounts unless listed.
        """
        
        if uploaded_file:
            img = Image.open(uploaded_file)
            resp = model.generate_content([prompt, img], stream=True)
        else:
            resp = model.generate_content(prompt, stream=True)
            
        full_res = ""
        box = st.empty()
        for chunk in resp:
            if chunk.text:
                full_res += chunk.text
                box.markdown(full_res + "▌")
        box.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})