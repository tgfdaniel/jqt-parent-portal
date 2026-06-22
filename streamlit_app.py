import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁基礎設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="", layout="centered")

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

st.markdown('<div class="custom-title"> JQT 訓練營查詢系統</div>', unsafe_allow_html=True)

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

    # 安全資料標準化清洗 (加入 errors='coerce' 防止空白日期崩潰)
    def standardize_df(df):
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce').dt.date
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
        # 尋找學員總表中所有符合身分證的列
        match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

        if not match.empty:
            student_name = match.iloc[0]['學員姓名']
            st.success(f"✅ 您好，{student_name} 同學/家長")
            
            if len(match) > 1:
                st.info(f"💡 系統偵測到您共報名了 {len(match)} 個課程項目，請點擊下方展開查看：")
            
            # --- 核心邏輯：巡迴渲染該學員的所有課程 ---
            for index, s in match.iterrows():
                student_cat = str(s.get('類別', '')).strip()
                student_venue = str(s.get('場地', '')).strip()
                student_class = str(s.get('班別', '')).strip()
                student_time = str(s.get('時段', '')).strip()
                
                try:
                    clean_lessons = int(float(s['剩餘堂數']))
                except:
                    clean_lessons = s.get('剩餘堂數', 0)

                # 建立動態卡片標題
                card_title = f"✨【{student_cat}】{student_class}" if student_cat else f"✨ {student_class}"
                if student_time and student_time != "nan":
                    card_title += f" ({student_time})"

                with st.expander(card_title, expanded=True):
                    
                    # 2x2 指標矩陣排版
                    row1_c1, row1_c2 = st.columns(2)
                    row1_c1.metric("上課場地", student_venue)
                    row1_c2.metric("剩餘堂數", f"{clean_lessons} 堂")
                    
                    st.markdown("#### 📋 本班級上課紀錄")

                    # --- 智能容錯篩選點名紀錄 ---
                    att_filter = (df_att['身分證字號'].astype(str).str.upper() == user_id)
                    if '類別' in df_att.columns and student_cat:
                        att_filter &= (df_att['類別'] == student_cat)
                    if '班別' in df_att.columns and student_class:
                        att_filter &= (df_att['班別'] == student_class)
                    
                    p_att = df_att[att_filter].copy()
                    
                    # --- 智能容錯篩選教學日誌 ---
                    log_filter = pd.Series(True, index=df_log.index)
                    if '類別' in df_log.columns and student_cat:
                        log_filter &= (df_log['類別'] == student_cat)
                    if '場地' in df_log.columns and student_venue:
                        log_filter &= (df_log['場地'] == student_venue)
                    if '班別' in df_log.columns and student_class:
                        log_filter &= (df_log['班別'] == student_class)
                    
                    filtered_logs = df_log[log_filter].copy()
                    if '日期' in filtered_logs.columns:
                        filtered_logs = filtered_logs[['日期', '今日教學內容']].drop_duplicates(subset=['日期'])

                    # 合併點名與日誌
                    if not p_att.empty:
                        if '日期' in p_att.columns and '日期' in filtered_logs.columns:
                            merged_df = pd.merge(p_att, filtered_logs, on='日期', how='left')
                        else:
                            merged_df = p_att
                            merged_df['今日教學內容'] = "暫無日誌連結"
                            
                        merged_df = merged_df.sort_values(by='日期', ascending=False)

                        for _, row in merged_df.iterrows():
                            # 兼容 Y/N 或 1/0 的出席狀態
                            is_present = str(row.get('出席', '')).strip().upper() in ["1", "1.0", "TRUE", "Y", "YES"]
                            status_icon = "✅ 出席" if is_present else "❌ 未出席"
                            
                            log_text = str(row.get('今日教學內容', '')).strip()
                            if not log_text or log_text == "nan":
                                log_text = "今日教練尚未上傳班級教學重點"
                                
                            p_comment = str(row.get('個人評語', "")).strip()
                            if p_comment == "nan":
                                p_comment = ""

                            comment_html = ""
                            if p_comment:
                                comment_html = f'<div style="margin-top:15px;padding:12px;background-color:#3d3d3d;border-radius:8px;border-left:5px solid #FFD700;"><div style="color:#FFD700;font-size:0.85rem;font-weight:bold;margin-bottom:5px;">💡 教練個人評語：</div><div style="color:#FFFFFF;font-size:1rem;line-height:1.5;white-space:pre-wrap;">{p_comment}</div></div>'

                            st.markdown(f"""
                                <div class="record-box"><span>📅 {row.get('日期', '未註明日期')}</span><span>{status_icon}</span></div>
                                <div class="content-box">
                                <div style="color:#AAAAAA;font-size:0.8rem;font-weight:bold;margin-bottom:8px;">🌟 班級教學重點：</div>
                                <div style="color:#E0E0E0;white-space:pre-wrap;line-height:1.4;">{log_text}</div>
                                {comment_html}
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("ℹ️ 該項目目前尚無上課點名紀錄。")
        else:
            st.error("❌ 查無資料，請核對身分證字號。")
except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e)

st.caption("© 2026 靖騰整合行銷有限公司")