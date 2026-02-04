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
    df_stu = conn.read(worksheet="學員總表", ttl=0).dropna(how='all')
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    df_att = conn.read(worksheet="點名紀錄", ttl=0).dropna(how='all')
    df_att.columns = [str(c).strip() for c in df_att.columns]
    df_log = conn.read(worksheet="教學日誌", ttl=0).dropna(how='all')
    df_log.columns = [str(c).strip() for c in df_log.columns]

    st.write("請輸入學員的身分證字號進行查詢")
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    if submit_btn and user_id:
        match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]
        if not match.empty:
            s = match.iloc[0]
            st.success(f"✅ 您好，{s['學員姓名']} 同學/家長")
            
            # --- 核心修正：消除小數點 ---
            try:
                # 先轉 float 處理像 "10.0" 的字串，再轉 int 去掉小數點
                clean_lessons = int(float(s['剩餘堂數']))
            except:
                # 如果萬一欄位裡填的是「尚未開課」之類的文字，就保持原樣
                clean_lessons = s['剩餘堂數']
            # --------------------------

            c1, c2 = st.columns(2)
            c1.metric("目前班別", s['班別'])
            c2.metric("剩餘堂數", f"{clean_lessons} 堂")
            
            st.divider()
            st.subheader("📋 上課紀錄與教學內容")

            p_att = df_att[df_att['身分證字號'].astype(str).str.upper() == user_id].copy().drop_duplicates(subset=['日期'])
            class_logs = df_log[df_log['班別'] == s['班別']][['日期', '今日教學內容']].drop_duplicates(subset=['日期'])
            merged_df = pd.merge(p_att, class_logs, on='日期', how='left').sort_values(by='日期', ascending=False)

            for index, row in merged_df.iterrows():
                status = "✅ 出席" if str(row['出席']) in ["1", "1.0", "1"] else "❌ 未出席"
                log_text = str(row['今日教學內容']) if pd.notna(row['今日教學內容']) else "教練尚未填寫日誌"
                p_comment = str(row.get('個人評語', "")) if pd.notna(row.get('個人評語')) else ""

                # 準備評語 HTML (縮排全部靠左，防止被誤判為代碼塊)
                comment_html = ""
                if p_comment.strip():
                    comment_html = f'<div style="margin-top:15px;padding:12px;background-color:#3d3d3d;border-radius:8px;border-left:5px solid #FFD700;"><div style="color:#FFD700;font-size:0.85rem;font-weight:bold;margin-bottom:5px;">💡 教練個人評語：</div><div style="color:#FFFFFF;font-size:1rem;line-height:1.5;white-space:pre-wrap;">{p_comment}</div></div>'

                # 一次性輸出完整卡片
                st.markdown(f"""
<div class="record-box"><span>📅 {row['日期']}</span><span>{status}</span></div>
<div class="content-box">
<div style="color:#AAAAAA;font-size:0.8rem;font-weight:bold;margin-bottom:8px;">🌟 班級教學重點：</div>
<div style="color:#E0E0E0;white-space:pre-wrap;">{log_text}</div>
{comment_html}
</div>
""", unsafe_allow_html=True)
                st.divider()
        else:
            st.error("❌ 查無資料")
except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")