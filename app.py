import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import json
import re
from PIL import Image

# --- 1. 基础配置 ---
try:
    INTERNAL_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=INTERNAL_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
except:
    st.error("⚠️ 密钥未配置，请检查 .streamlit/secrets.toml")
    st.stop()

# --- 2. 核心：简单直接的数据读取 ---
# 既然文件名确定了，我们就直接读，不再搞复杂的搜索
FILE_PATH_NEW = "data/iHisto Inc_Product_Service List(20260120).csv"
FILE_PATH_OLD = "data/iHisto Inc_Product_Service List.csv"

@st.cache_data(show_spinner=False)
def load_data_simple():
    # 1. 确定文件路径
    if os.path.exists(FILE_PATH_NEW):
        target_file = FILE_PATH_NEW
    elif os.path.exists(FILE_PATH_OLD):
        target_file = FILE_PATH_OLD
    else:
        # 尝试在根目录找
        if os.path.exists("iHisto Inc_Product_Service List(20260120).csv"):
            target_file = "iHisto Inc_Product_Service List(20260120).csv"
        else:
            return None, "❌ 未找到 CSV 文件", 0

    # 2. 读取数据 (尝试两种标题位置)
    try:
        # 方案 A: 假设标题在第 1 行 (header=0) -> 针对 20260120 新版
        df = pd.read_csv(target_file, header=0)
        
        # 检查是否读对了：看看列名里有没有 "Product" 相关的字
        # 如果列名不对，说明 header=0 读错了，尝试 header=3
        cols = str(list(df.columns))
        if "Product" not in cols and "Service" not in cols:
            df = pd.read_csv(target_file, header=3) # 方案 B: 旧版格式
        
        # 3. 整理数据文本
        service_text = ""
        count = 0
        he_found = False
        
        for index, row in df.iterrows():
            # 容错处理：获取列名（防止列名有微小差异）
            # 找到包含 'Product' 的列作为 Name，包含 'Price' 的列作为 Price
            col_name = next((c for c in df.columns if 'Product' in str(c) or 'Service' in str(c)), None)
            col_price = next((c for c in df.columns if 'Price' in str(c) or 'Sales' in str(c)), None)
            col_desc = next((c for c in df.columns if 'Memo' in str(c) or 'Description' in str(c)), None)
            
            if not col_name or not col_price:
                continue

            name = str(row[col_name]).strip()
            price = str(row[col_price]).strip()
            desc = str(row[col_desc]).strip() if col_desc else ""

            if name == 'nan' or not name: continue
            if price == 'nan': price = ""
            
            # 检查 H&E
            if "H&E" in name:
                he_found = True

            service_text += f"ITEM: {name} | PRICE: ${price}\nDETAILS: {desc}\n---\n"
            count += 1
            
        status_msg = f"已加载 {count} 项服务。"
        if he_found:
            status_msg += " (✅ H&E 已找到)"
        else:
            status_msg += " (❌ H&E 未找到)"
            
        return service_text, status_msg, count

    except Exception as e:
        return None, f"❌ 读取出错: {e}", 0

# 执行加载
IHISTO_SERVICES, STATUS_MSG, TOTAL_COUNT = load_data_simple()

# --- 3. 页面界面 (恢复简洁版) ---
st.set_page_config(page_title="iHisto AI", page_icon="🔬")

# 侧边栏：只显示最核心的状态
with st.sidebar:
    st.title("系统状态")
    if TOTAL_COUNT > 0:
        st.success(STATUS_MSG)
        # 调试开关
        if st.checkbox("查看原始数据文本"):
            st.text_area("Data Preview", IHISTO_SERVICES, height=300)
    else:
        st.error(STATUS_MSG)
        
    if st.button("刷新数据"):
        st.cache_data.clear()
        st.rerun()

# 主标题
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("images/color_logo-h.png"):
        st.image("images/color_logo-h.png", width=80)
    else:
        st.write("🔬")
with col2:
    st.title("iHisto Scientific Assistant")
st.markdown("---")

# --- 4. 聊天逻辑 ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome! Please verify your Name, Email, and Company."}]

if "client_info" not in st.session_state:
    st.session_state.client_info = {"name": None, "email": None, "company": None}
    st.session_state.is_identified = False

# 显示历史消息
for msg in st.session_state.messages:
    avatar = "images/new_logo.png" if msg["role"] == "assistant" and os.path.exists("images/new_logo.png") else None
    st.chat_message(msg["role"], avatar=avatar).markdown(msg["content"])

# 文件上传区 (简洁版，放在侧边栏或者是单独区域)
with st.sidebar:
    uploaded_file = st.file_uploader("上传图片 (可选)", type=["png", "jpg", "jpeg"])

# 聊天输入框
user_input = st.chat_input("请输入您的问题...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 1. 身份验证逻辑
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
                    st.session_state.messages.append({"role": "assistant", "content": f"Thanks {data['name']}! Verified. ✅"})
                    st.rerun()
                else:
                    st.session_state.messages.append({"role": "assistant", "content": "I still need your full details (Name, Email, Company)."})
            else:
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
        except: st.error("Verification Error")
    
    # 2. 业务咨询逻辑
    else:
        prompt = f"""
        ACT AS: iHisto Scientific Consultant.
        
        DATABASE:
        {IHISTO_SERVICES}
        
        USER QUERY: "{user_input}"
        
        RULES:
        1. Search the DATABASE for the requested service.
        2. Quote the EXACT price from the database.
        3. For "H&E", look for "Routine Histology:H&E Staining".
        4. No guessing.
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