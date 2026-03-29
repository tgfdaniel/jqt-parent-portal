import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁基礎設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="🏀", layout="centered")

# --- CSS 樣式設定 ---
st.markdown("""
<style>
/* 這是調整「場地、目前班別」下方具體內容的字體大小 */
[data-testid="stMetricValue"] {
    font-size: 1.2rem !important; 
}

/* 這是調整上方小標籤（場地、目前班別）的字體大小 */
[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
}
[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu, header, footer {visibility: hidden;}
.block-container { padding-top: 2rem !important; }
.custom-title {
    background-color: #1E1E1E; color: #FFFFFF; font-size: 22px; font-weight: 700;
    text-align: center; padding: 15px; border-radius: 12px; margin-bottom: 25px;
}
.record-box {
    background-color: #333333; color: #FFFFFF; padding: 10px 15px;
    border-radius: 10px 10px 0 0; font-weight: bold; display: flex;
    justify-content: space-between; margin-top: 15px;
}
.content-box {
    background-color: #262626; color: #E0E0E0; padding: 12px 15px;
    border-radius: 0 0 10px 10px; line-height: 1.6; border: 1px solid #333333;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="custom-title">🏀 JQT 訓練營查詢系統</div>', unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. 讀取三張核心表
    df_stu = conn.read(worksheet="學員總表", ttl=0).dropna(how='all')
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    
    df_att = conn.read(worksheet="點名紀錄", ttl=0).dropna(how='all')
    df_att.columns = [str(c).strip() for c in df_att.columns]

    df_log = conn.read(worksheet="教學日誌", ttl=0).dropna(how='all')
    df_log.columns = [str(c).strip() for c in df_log.columns]

    # --- 核心修正 A：統一日期與場地格式 (防止匹配不到) ---
    def standardize_df(df):
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期']).dt.date # 強制轉為 YYYY-MM-DD
        if '場地' in df.columns:
            df['場地'] = df['場地'].astype(str).str.strip()
        if '班別' in df.columns:
            df['班別'] = df['班別'].astype(str).str.strip()
        return df

    df_att = standardize_df(df_att)
    df_log = standardize_df(df_log)

    # 2. 查詢介面
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    if submit_btn and user_id:
        match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

        if not match.empty:
            s = match.iloc[0]
            student_name = s['學員姓名']
            student_venue = str(s['場地']).strip()  # 取得場地
            student_class = str(s['班別']).strip()  # 取得班別
            
            st.success(f"✅ 您好，{student_name} 同學/家長")
            
            # 堂數轉換 (處理小數點問題)
            try:
                clean_lessons = int(float(s['剩餘堂數']))
            except:
                clean_lessons = s['剩餘堂數']

            # --- 修改：改為三欄式顯示 ---
            c1, c2, c3 = st.columns(3)
            c1.metric("場地", student_venue)
            c2.metric("目前班別", student_class)
            c3.metric("剩餘堂數", f"{clean_lessons} 堂")
            
            st.divider()
            st.subheader("📋 上課紀錄與教學內容")

            # --- 核心邏輯：精準合併 (日期 + 場地 + 班別) ---
            
            # A. 取得該學員的點名紀錄
            p_att = df_att[df_att['身分證字號'].astype(str).str.upper() == user_id].copy()
            
            # B. 取得對應的教學日誌 (嚴格比對場地與班別)
            filtered_logs = df_log[
                (df_log['場地'] == student_venue) & 
                (df_log['班別'] == student_class)
            ].copy()
            
            # 簡化日誌表
            filtered_logs = filtered_logs[['日期', '今日教學內容']].drop_duplicates(subset=['日期'])

            # C. 執行合併
            merged_df = pd.merge(p_att, filtered_logs, on='日期', how='left')
            merged_df = merged_df.sort_values(by='日期', ascending=False)
            
            # 簡化日誌表，準備合併
            filtered_logs = filtered_logs[['日期', '今日教學內容']].drop_duplicates(subset=['日期'])

            # C. 以「日期」為唯一 Key 進行左合併
            merged_df = pd.merge(p_att, filtered_logs, on='日期', how='left')
            merged_df = merged_df.sort_values(by='日期', ascending=False)

            if not merged_df.empty:
                for index, row in merged_df.iterrows():
                    status_icon = "✅ 出席" if str(row['出席']) in ["1", "1.0", "TRUE", "True"] else "❌ 未出席"
                    
                    # 抓取對應日期的教學內容
                    log_text = str(row['今日教學內容']).strip() if pd.notna(row['今日教學內容']) else "今日教練尚未上傳班級教學重點"
                    p_comment = str(row.get('個人評語', "")).strip() if pd.notna(row.get('個人評語')) else ""

                    # 評語 HTML
                    comment_html = ""
                    if p_comment:
                        comment_html = f'<div style="margin-top:15px;padding:12px;background-color:#3d3d3d;border-radius:8px;border-left:5px solid #FFD700;"><div style="color:#FFD700;font-size:0.85rem;font-weight:bold;margin-bottom:5px;">💡 教練個人評語：</div><div style="color:#FFFFFF;font-size:1rem;line-height:1.4;white-space:pre-wrap;">{p_comment}</div></div>'

                    # 渲染顯示卡片
                    st.markdown(f"""
                        <div class="record-box"><span>📅 {row['日期']}</span><span>{status_icon}</span></div>
                        <div class="content-box">
                        <div style="color:#AAAAAA;font-size:0.8rem;font-weight:bold;margin-bottom:8px;">🌟 班級教學重點：</div>
                        <div style="color:#E0E0E0;white-space:pre-wrap;line-height:1.3;font-size:0.95rem;">{log_text}</div>
                        {comment_html}
                        </div>
                    """, unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("目前尚無上課點名紀錄。")
        else:
            st.error("❌ 查無資料，請核對身分證字號。")
except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")
