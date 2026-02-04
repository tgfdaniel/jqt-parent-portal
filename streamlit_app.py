import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁基礎設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="🏀", layout="centered")

# --- 終極版 CSS (黑底、隱藏元件、自定義標題) ---
st.markdown("""
    <style>
    [data-testid="stStatusWidget"], .stStatusWidget { display: none !important; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 2rem !important; }

    .custom-title {
        background-color: #1E1E1E !important;
        color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        text-align: center !important;
        padding: 15px 10px !important;
        border-radius: 12px !important;
        margin-bottom: 25px !important;
        display: block !important;
    }
    .record-box {
        background-color: #333333 !important;
        color: #FFFFFF !important;
        padding: 10px 15px !important;
        border-radius: 10px 10px 0 0 !important;
        font-weight: bold !important;
        display: flex !important;
        justify-content: space-between !important;
        margin-top: 15px !important;
    }
    .content-box {
        background-color: #262626 !important;
        color: #E0E0E0 !important;
        padding: 12px 15px !important;
        border-radius: 0 0 10px 10px !important;
        line-height: 1.6 !important;
        border: 1px solid #333333 !important;
        margin-bottom: 10px !important;
    }
    @media (max-width: 600px) {
        .custom-title { font-size: 18px !important; }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="custom-title">🏀 JQT 訓練營查詢系統</p>', unsafe_allow_html=True)

# 2. 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# --- A. 讀取資料 (放在 try 裡面確保安全) ---
try:
    df_stu = conn.read(worksheet="學員總表", ttl=0).dropna(how='all')
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    
    df_att = conn.read(worksheet="點名紀錄", ttl=0).dropna(how='all')
    df_att.columns = [str(c).strip() for c in df_att.columns]

    df_log = conn.read(worksheet="教學日誌", ttl=0).dropna(how='all')
    df_log.columns = [str(c).strip() for c in df_log.columns]

    # --- B. 查詢介面 ---
    st.write("請輸入學員的身分證字號進行查詢")
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    # --- C. 搜尋與顯示邏輯 (重點：全部都要縮排在 try 裡面) ---
    if submit_btn:
        if not user_id:
            st.warning("⚠️ 請先輸入身分證字號。")
        else:
            # 搜尋學員
            match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

            if not match.empty:
                s = match.iloc[0]
                student_name = s['學員姓名']
                student_class = s['班別']
                
                st.success(f"✅ 您好，{student_name} 同學/家長")
                        
                c1, c2 = st.columns(2)
                c1.metric("目前班別", student_class)
                try:
                    lessons = int(float(s['剩餘堂數']))
                except:
                    lessons = s['剩餘堂數']
                c2.metric("剩餘總堂數", f"{lessons} 堂")
                
                st.divider()
                st.subheader("📋 上課紀錄與教學內容")

                # 1. 篩選與去重
                p_att = df_att[df_att['身分證字號'].astype(str).str.upper() == user_id].copy()
                p_att = p_att.drop_duplicates(subset=['日期']) 

                class_logs = df_log[df_log['班別'] == student_class][['日期', '今日教學內容']]
                class_logs = class_logs.drop_duplicates(subset=['日期'])

                # 2. 合併資料
                merged_df = pd.merge(p_att, class_logs, on='日期', how='left')

                if not merged_df.empty:
                    merged_df = merged_df.sort_values(by='日期', ascending=False)

                    # 3. 循環顯示卡片
                    for index, row in merged_df.iterrows():
                        status_icon = "✅ 出席" if str(row['出席']) in ["1", "1.0", "1"] else "❌ 未出席"
                        log_text = str(row['今日教學內容']) if pd.notna(row['今日教學內容']) else "教練尚未填寫日誌"
                        personal_comment = str(row.get('個人評語', "")) if pd.notna(row.get('個人評語')) else ""

                        comment_html = ""
                        if personal_comment.strip():
                            comment_html = f"""
                            <div style="margin-top: 15px; padding: 12px; background-color: #3d3d3d; border-radius: 8px; border-left: 5px solid #FFD700;">
                                <div style="color: #FFD700; font-size: 0.85rem; font-weight: bold; margin-bottom: 5px;">💡 教練個人評語：</div>
                                <div style="color: #FFFFFF; font-size: 1rem; line-height: 1.5;">{personal_comment}</div>
                            </div>
                            """

                        st.markdown(f"""
                            <div class="record-box">
                                <span>📅 {row['日期']}</span>
                                <span>{status_icon}</span>
                            </div>
                            <div class="content-box">
                                <div style="color: #AAAAAA; font-size: 0.8rem; font-weight: bold; margin-bottom: 8px;">🌟 班級教學重點：</div>
                                <div style="color: #E0E0E0; white-space: pre-wrap;">{log_text}</div>
                                {comment_html}
                            </div>
                        """, unsafe_allow_html=True)
                        st.divider()
                else:
                    st.info("目前尚無上課點名紀錄。")
            else:
                st.error("❌ 查無資料，請核對身分證字號。")

# 這裡才是 try 的結束
except Exception as e:
    st.error("⚠️ 系統讀取錯誤，請檢查試算表欄位名稱")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")