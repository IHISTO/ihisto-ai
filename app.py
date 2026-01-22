import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import json
import re
from PIL import Image

# --- 1. Configuration ---
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    st.error("⚠️ Key Missing. Check secrets.toml")
    st.stop()

# --- 2. ⚡️ 极速透明数据加载器 ---
DATA_DIRS = ["data", "."] 
TARGET_FILENAME = "iHisto Inc_Product_Service List(20260120).csv"
BACKUP_FILENAME = "iHisto Inc_Product_Service List.csv"

def load_data_debug():
    logs = []
    found_path = None
    
    # 1. 🔍 侦查阶段
    logs.append("--- File System Check ---")
    for d in DATA_DIRS:
        if os.path.exists(d):
            files = os.listdir(d)
            # 过滤出csv文件
            csvs = [f for f in files if f.endswith('.csv')]
            logs.append(f"📁 Folder '{d}': Found {csvs}")
            
            if TARGET_FILENAME in files:
                found_path = os.path.join(d, TARGET_FILENAME)
            elif BACKUP_FILENAME in files and found_path is None:
                found_path = os.path.join(d, BACKUP_FILENAME)
        else:
            logs.append(f"❌ Folder '{d}' does not exist.")
            
    if not found_path:
        return None, logs, "❌ ERROR: Target CSV not found."

    # 2. 📖 读取阶段
    try:
        logs.append(f"👉 Loading: {found_path}")
        
        # 智能找标题
        header_idx = 0
        with open(found_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:20]):
                if "Product/Service full name" in line:
                    header_idx = i
                    break
        
        logs.append(f"📏 Header Row: {header_idx + 1}")
        
        df = pd.read_csv(found_path, header=header_idx)
        
        # 3. 解析阶段
        service_text = ""
        he_status = "❌ H&E MISSING"
        count = 0
        
        for index, row in df.iterrows():
            name = str(row['Product/Service full name']).strip()
            price = str(row['Sales price']).strip()
            desc = str(row['Memo/Description']).strip()

            if name == 'nan': name = ""
            if price == 'nan': price = ""
            if desc == 'nan': desc = ""

            # 🔎 重点监控 H&E
            if "H&E" in name and "Staining" in name:
                he_status = f"✅ Found: '{name}' -> ${price}"

            if name:
                service_text += f"ITEM: {name} | PRICE: ${price}\nDETAILS: {desc}\n---\n"
                count += 1
                
        logs.append(f"📦 Loaded {count} items.")
        return service_text, logs, he_status

    except Exception as e:
        return None, logs, f"❌ Error: {e}"

# 执行加载
IHISTO_SERVICES, DEBUG_LOGS, HE_STATUS = load_data_debug()

# --- Page Setup ---
st.set_page_config(page_title="iHisto Debug", page_icon="🛠️")

# CSS
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

# --- Sidebar (真相大白区) ---
with st.sidebar:
    st.title("🕵️‍♀️ Sherlock Debugger")
    
    if "✅" in HE_STATUS:
        st.success("H&E Price Loaded!")
        st.info(HE_STATUS) 
    else:
        st.error("H&E Price Missing!")
    
    with st.expander("View Logs"):
        for log in DEBUG_LOGS:
            st.text(log)
            
    if st.button("🧹 Reset"):
        st.cache_data.clear()
        st.rerun()

# --- Main Logic ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("images/color_logo-h.png"):
        st.image("images/color_logo-h.png", use_container_width=True)
    else:
        st.markdown("### iHisto AI")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome! Please verify Name, Email, Company."}]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

for msg in st.session_state.messages:
    avatar = "images/new_logo.png" if msg["role"] == "assistant" and os.path.exists("images/new_logo.png") else None
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

popover = st.popover("➕")
with popover:
    st.markdown("### Upload")
    uploaded_file = st.file_uploader("File", label_visibility="collapsed")
    if uploaded_file: st.success("Uploaded!")

if st.button("🔄"):
    if st.session_state.is_identified:
         st.session_state.messages = [{"role": "assistant", "content": "Chat cleared."}]
    else:
         st.session_state.messages = [{"role": "assistant", "content": "Welcome! Please verify Name, Email, Company."}]
         st.session_state.client_info = {"name": None, "email": None, "company": None}
         st.session_state.is_identified = False
    st.rerun()

user_input = st.chat_input("Ask me...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    if not st.session_state.is_identified:
        try:
            info_str = json.dumps(st.session_state.client_info)
            resp = model.generate_content(f"Extract Name,Email,Company from '{user_input}'. Current: {info_str}. Output JSON: ###DATA: {{...}}###")
            match = re.search(r'###DATA: ({.*?})###', resp.text)
            if match:
                data = json.loads(match.group(1))
                st.session_state.client_info = data
                if all(data.values()):
                    st.session_state.is_identified = True
                    st.session_state.messages.append({"role": "assistant", "content": f"Thanks {data['name']}! Verified. ✅"})
                    st.rerun()
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "I still need details."})
            else:
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
        except: st.error("Error")
    else:
        prompt = f"""
        ACT AS: iHisto Consultant.
        DATA:
        {IHISTO_SERVICES}
        USER: "{user_input}"
        RULES:
        1. STRICTLY use DATA prices.
        2. H&E = "Routine Histology:H&E Staining".
        3. IF DATA says $6.00, SAY $6.00.
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