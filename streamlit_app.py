import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁基礎設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="🏀", layout="centered")

# --- 終極版 CSS 樣式設定 ---
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

st.markdown('<div class="custom-title">🏆 JQT 訓練營查詢系統</div>', unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. 讀取資料
    df_stu = conn.read(worksheet="學員總表", ttl=0).dropna(how='all')
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    
    df_att = conn.read(worksheet="點名紀錄", ttl=0).dropna(how='all')
    df_att.columns = [str(c).strip() for c in df_att.columns]

    df_log = conn.read(worksheet="教學日誌", ttl=0).dropna(how='all')
    df_log.columns = [str(c).strip() for c in df_log.columns]

    # 欄位名稱相容性清洗 (將可能的 '球類別' 統一對齊為 '類別')
    for df in [df_stu, df_att, df_log]:
        if '球類別' in df.columns and '類別' not in df.columns:
            df.rename(columns={'球類別': '類別'}, inplace=True)

    # 資料標準化清洗
    def standardize_df(df):
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期']).dt.date
        for col in ['類別', '場地', '班別', '時段']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        return df

    df_stu = standardize_df(df_stu)
    df_att = standardize_df(df_att)
    df_log = standardize_df(df_log)

    # 2. 查詢介面
    st.write("請輸入學員的身分證字號進行查詢")
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    if submit_btn and user_id:
        # 尋找學員總表中所有符合身分證的列 (可能有多列)
        match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

        if not match.empty:
            student_name = match.iloc[0]['學員姓名']
            st.success(f"✅ 您好，{student_name} 同學/家長")
            st.info(f"💡 系統偵測到您共報名了 {len(match)} 個課程項目，請點擊下方展開查看：")
            
            # --- 核心邏輯升級：巡迴渲染該學員的所有課程 ---
            for index, s in match.iterrows():
                student_cat = s['類別']
                student_venue = s['場地']
                student_class = s['班別']
                student_time = s['時段']
                
                try:
                    clean_lessons = int(float(s['剩餘堂數']))
                except:
                    clean_lessons = s['剩餘堂數']

                # 為每個課程建立專屬的 Expander 卡片
                with st.expander(f"✨【{student_cat}】{student_class} ({student_time})", expanded=True):
                    
                    # 2x2 指標矩陣排版
                    row1_c1, row1_c2 = st.columns(2)
                    row1_c1.metric("上課場地", student_venue)
                    row1_c2.metric("剩餘堂數", f"{clean_lessons} 堂")
                    
                    st.markdown("#### 📋 本班級上課紀錄")

                    # 三重條件精準篩選個人點名紀錄 (身分證 + 類別 + 班別)
                    p_att = df_att[
                        (df_att['身分證字號'].astype(str).str.upper() == user_id) & 
                        (df_att['類別'] == student_cat) & 
                        (df_att['班別'] == student_class)
                    ].copy()
                    
                    # 篩選對應的班級教學日誌 (類別 + 場地 + 班別)
                    filtered_logs = df_log[
                        (df_log['類別'] == student_cat) & 
                        (df_log['場地'] == student_venue) & 
                        (df_log['班別'] == student_class)
                    ].copy()
                    
                    filtered_logs = filtered_logs[['日期', '今日教學內容']].drop_duplicates(subset=['日期'])

                    # 合併點名與日誌
                    if not p_att.empty:
                        merged_df = pd.merge(p_att, filtered_logs, on='日期', how='left')
                        merged_df = merged_df.sort_values(by='日期', ascending=False)

                        for _, row in merged_df.iterrows():
                            status_icon = "✅ 出席" if str(row['出席']).strip().upper() in ["1", "1.0", "TRUE", "Y", "YES"] else "❌ 未出席"
                            log_text = str(row['今日教學內容']).strip() if pd.notna(row['今日教學內容']) else "今日教練尚未上傳班級教學重點"
                            p_comment = str(row.get('個人評語', "")).strip() if pd.notna(row.get('個人評語')) else ""

                            comment_html = ""
                            if p_comment:
                                comment_html = f'<div style="margin-top:15px;padding:12px;background-color:#3d3d3d;border-radius:8px;border-left:5px solid #FFD700;"><div style="color:#FFD700;font-size:0.85rem;font-weight:bold;margin-bottom:5px;">💡 教練個人評語：</div><div style="color:#FFFFFF;font-size:1rem;line-height:1.5;white-space:pre-wrap;">{p_comment}</div></div>'

                            st.markdown(f"""
                                <div class="record-box"><span>📅 {row['日期']}</span><span>{status_icon}</span></div>
                                <div class="content-box">
                                <div style="color:#AAAAAA;font-size:0.8rem;font-weight:bold;margin-bottom:8px;">🌟 班級教學重點：</div>
                                <div style="color:#E0E0E0;white-space:pre-wrap;line-height:1.4;">{log_text}</div>
                                {comment_html}
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("ℹ️ 該項目目前尚無上課點名紀錄。")
        else:
            st.error("❌ 查善資料，請核對身分證字號。")
except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")