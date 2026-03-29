import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁基礎設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="🏀", layout="centered")

# --- CSS 樣式設定 ---
st.markdown("""
<style>
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
    # 1. 讀取資料
    df_stu = conn.read(worksheet="學員總表", ttl=0).dropna(how='all')
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    
    df_att = conn.read(worksheet="點名紀錄", ttl=0).dropna(how='all')
    df_att.columns = [str(c).strip() for c in df_att.columns]

    df_log = conn.read(worksheet="教學日誌", ttl=0).dropna(how='all')
    df_log.columns = [str(c).strip() for c in df_log.columns]

    # --- 核心修正 A：強制日期格式統一 (防止 3/28 與 3/29 混淆) ---
    def clean_date(df):
        if '日期' in df.columns:
            # errors='coerce' 會把不合法的日期變成空值，避免程式崩潰
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce').dt.date
        return df

    df_att = clean_date(df_att)
    df_log = clean_date(df_log)

    # 2. 查詢介面
    st.write("請輸入學員的身分證字號進行查詢")
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    if submit_btn and user_id:
        match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

        if not match.empty:
            s = match.iloc[0]
            student_name = s['學員姓名']
            student_class = str(s['班別']).strip() # 抓取學生正確的班別
            
            st.success(f"✅ 您好，{student_name} 同學/家長")
            
            # 堂數轉換
            try:
                clean_lessons = int(float(s['剩餘堂數']))
            except:
                clean_lessons = s['剩餘堂數']

            c1, c2 = st.columns(2)
            c1.metric("目前班別", student_class)
            c2.metric("剩餘堂數", f"{clean_lessons} 堂")
            
            st.divider()
            st.subheader("📋 上課紀錄與教學內容")

            # --- 核心修正 B：精準合併邏輯 ---
            
            # A. 抓點名紀錄 (確保日期已經過標準化)
            p_att = df_att[df_att['身分證字號'].astype(str).str.upper() == user_id].copy()
            
            # B. 抓日誌：必須「班別」與「日期」同時對齊
            # 這裡先篩選出該學員所屬的班別，避免抓到別場的日誌
            class_logs = df_log[df_log['班別'].astype(str).str.strip() == student_class].copy()
            class_logs = class_logs[['日期', '今日教學內容']].drop_duplicates(subset=['日期'])

            # C. 執行合併 (on='日期')
            merged_df = pd.merge(p_att, class_logs, on='日期', how='left')
            merged_df = merged_df.sort_values(by='日期', ascending=False)

            if not merged_df.empty:
                for index, row in merged_df.iterrows():
                    status_icon = "✅ 出席" if str(row['出席']) in ["1", "1.0", "1"] else "❌ 未出席"
                    
                    # 抓取日誌內容
                    log_text = str(row['今日教學內容']).strip() if pd.notna(row['今日教學內容']) else "教練尚未填寫今日教學重點"
                    p_comment = str(row.get('個人評語', "")).strip() if pd.notna(row.get('個人評語')) else ""

                    # 評語 HTML
                    comment_html = ""
                    if p_comment:
                        comment_html = f'<div style="margin-top:15px;padding:12px;background-color:#3d3d3d;border-radius:8px;border-left:5px solid #FFD700;"><div style="color:#FFD700;font-size:0.85rem;font-weight:bold;margin-bottom:5px;">💡 教練個人評語：</div><div style="color:#FFFFFF;font-size:1rem;line-height:1.5;white-space:pre-wrap;">{p_comment}</div></div>'

                    # 顯示卡片
                    st.markdown(f"""
                        <div class="record-box"><span>📅 {row['日期']}</span><span>{status_icon}</span></div>
                        <div class="content-box">
                        <div style="color:#AAAAAA;font-size:0.8rem;font-weight:bold;margin-bottom:8px;">🌟 班級教學重點：</div>
                        <div style="color:#E0E0E0;white-space:pre-wrap;line-height:1.4;">{log_text}</div>
                        {comment_html}
                        </div>
                    """, unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("目前尚無上課紀錄。")
        else:
            st.error("❌ 查無資料")
except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")
