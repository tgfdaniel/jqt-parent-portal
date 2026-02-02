import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 網頁標題與樣式設定
st.set_page_config(page_title="JQT 訓練營查詢系統", page_icon="🏀", layout="centered")
# 用 Markdown 搭配剛才定義的 class 來顯示標題
st.markdown('<p class="custom-title">🏀 JQT 訓練營查詢系統</p>', unsafe_allow_html=True)

# 隱藏右上的 Running 狀態與選單
# 強化版 CSS：強制執行黑底白字，防止被系統覆蓋
hide_style = """
    <style>
    /* 1. 隱藏系統元件 (維持不變) */
    [data-testid="stStatusWidget"], .stStatusWidget { display: none !important; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 2rem !important; }

    /* 2. 頂部標題：強制黑底白字 */
    .custom-title {
        background-color: #1E1E1E !important; /* 強制背景為深黑 */
        color: #FFFFFF !important;            /* 強制字體為純白 */
        font-size: 22px !important;
        font-weight: 700 !important;
        text-align: center !important;
        padding: 15px 10px !important;
        border-radius: 12px !important;
        margin-bottom: 25px !important;
        display: block !important;           /* 確保區塊完整顯示 */
    }

    /* 3. 日期出席列 */
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

    /* 4. 教學內容區 */
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
"""
st.markdown(hide_style, unsafe_allow_html=True)

# 2. 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # --- A. 讀取資料 ---
    df_stu = conn.read(worksheet="學員總表", ttl=0)
    df_stu.columns = [str(c).strip() for c in df_stu.columns]
    
    df_att = conn.read(worksheet="點名紀錄", ttl=0)
    df_att.columns = [str(c).strip() for c in df_att.columns]

    df_log = conn.read(worksheet="教學日誌", ttl=0)
    df_log.columns = [str(c).strip() for c in df_log.columns]

    # --- B. 查詢介面 ---
    st.write("請輸入學員的身分證字號進行查詢")
    user_id = st.text_input("學員身分證字號", placeholder="例如: A123456789").strip().upper()
    submit_btn = st.button("確認查詢")

    # --- C. 搜尋與顯示邏輯 (這裡的縮排必須對齊) ---
    if submit_btn:
        if user_id:
            # 搜尋學員
            match = df_stu[df_stu['身分證字號'].astype(str).str.upper() == user_id]

            if not match.empty:
                s = match.iloc[0]
                student_name = s['學員姓名']
                student_class = s['班別']
                
                st.success(f"✅ 您好，{student_name} 同學/同學家長")
                        
                # 顯示數據卡片
                c1, c2 = st.columns(2)
                c1.metric("目前班別", student_class)
                try:
                    lessons = int(float(s['剩餘堂數']))
                except:
                    lessons = s['剩餘堂數']
                c2.metric("剩餘總堂數", f"{lessons} 堂")
                
                st.divider()
                
                # --- 整合表格區 ---
                st.subheader("📋 上課紀錄與教學內容")

                # 1. 篩選點名紀錄
                p_att = df_att[df_att['身分證字號'].astype(str).str.upper() == user_id].copy()

                # 2. 篩選班別教學日誌
                class_logs = df_log[df_log['班別'] == student_class][['日期', '今日教學內容']]

                # 3. 合併資料 (根據日期)
                merged_df = pd.merge(p_att, class_logs, on='日期', how='left')

                if not merged_df.empty:
                    # 排序：新的在上面
                    merged_df = merged_df.sort_values(by='日期', ascending=False)

                    # 格式化出席狀態
                    merged_df['出席狀態'] = merged_df['出席'].apply(
                        lambda x: "✅ 出席" if str(x) in ["1", "1.0", "1"] else "❌ 未出席"
                    )
                    
                    # 處理空內容
                    merged_df['今日教學內容'] = merged_df['今日教學內容'].fillna("教練尚未填寫日誌")

                    # --- 1. 定義灰底樣式 (CSS) ---
                    st.markdown("""
                        <style>
                        .record-box {
                            background-color: #f0f2f6;
                            padding: 10px 15px;
                            border-radius: 10px;
                            font-weight: bold;
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            color: #31333F;
                            margin-top: 15px;
                        }
                        .content-box {
                            padding: 10px 15px 5px 15px;
                            line-height: 1.6;
                            color: #555;
                        }
                        </style>
                    """, unsafe_allow_html=True)

                    # --- 2. 循環顯示卡片 ---
                    for index, row in merged_df.iterrows():
                        # 灰底標題列 (日期 + 出席)
                        st.markdown(f"""
                            <div class="record-box">
                                <span>📅 {row['日期']}</span>
                                <span>{row['出席狀態']}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # 教學內容與個人評語區
                        # 增加一個判斷：如果有評語才顯示評語區塊
                        coach_comment = ""
                        # 假設你的欄位名稱是 "個人評語"
                        if pd.notna(row.get('個人評語')) and row['個人評語'] != "":
                            coach_comment = f"""
                            <div style="margin-top: 10px; padding: 8px; background-color: #3d3d3d; border-radius: 5px; border-left: 4px solid #FFD700;">
                                <span style="color: #FFD700; font-size: 0.8rem; font-weight: bold;">💡 教練評語：</span><br>
                                <span style="color: #FFFFFF;">{row['個人評語']}</span>
                            </div>
                            """

                        st.markdown(f"""
                            <div class="content-box">
                                <div style="color: #AAAAAA; font-size: 0.8rem; font-weight: bold; margin-bottom: 5px;">🌟 班級教學重點：</div>
                                {row['今日教學內容']}
                                {coach_comment}
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.divider()
                else:
                    st.info("目前尚無上課點名紀錄。")
            else:
                st.error("❌ 查無資料，請核對身分證字號。")
        else:
            st.warning("⚠️ 請先輸入身分證字號。")

except Exception as e:
    st.error("⚠️ 系統讀取錯誤")
    st.exception(e) # 這行能幫我們抓到還有哪個欄位名稱不對

st.caption("© 2026 靖騰整合行銷有限公司")