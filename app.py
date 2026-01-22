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
            left: 20px;  /* 电脑上距离左边 20px */
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
            right: 20px; /* 电脑上距离右边 20px */
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