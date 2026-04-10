import io
import time
import re
from pathlib import Path
import pandas as pd
import streamlit as st

from crawler_logic import crawl_products

st.set_page_config(
    page_title="OMD Data MegaMarket Crawler",
    page_icon="🛒",
    layout="wide",
)

def clean_input(raw_kw: str) -> str:
    if not raw_kw: return ""
    
    # 1. Chuyển sang chữ hoa để dễ xử lý
    kw = raw_kw.upper()
    
    # 2. Loại bỏ các ký hiệu số lượng thùng/lốc ở cuối (VD: *24, *30, X6, X12)
    # Đã sửa lỗi \x ở đây thành [*X]
    kw = re.sub(r'[\*X]\s?\d+$', '', kw)
    
    # 3. Loại bỏ quy cách đóng gói kỹ thuật (VD: /80G, /140G, 3.6/3.5KG, 80/81G)
    kw = re.sub(r'\d+(\.\d+)?(/\d+(\.\d+)?)?\s?(G|GR|KG|L|ML)', '', kw)
    
    # 4. Loại bỏ các mã loại bao bì/viết tắt phổ biến của hệ thống POS
    pos_terms = ['MILY ', 'HANDY', 'HT ', 'PET ', 'NGK ', 'SB ', 'NRC ', 'NX ', 'DD ', 'OMC', 'T-OT']
    for term in pos_terms:
        kw = kw.replace(term, ' ')
        
    # 5. Thay thế các dấu đặc biệt thành khoảng trắng
    kw = re.sub(r'[\.\/\-\*\(\)]', ' ', kw)
    
    # 6. Loại bỏ khoảng trắng thừa
    kw = " ".join(kw.split())
    
    return kw.capitalize()
    
    
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(keyword: str):
    result = crawl_products(keyword, output_dir=BASE_DIR)
    if result.get("success") and result.get("file_bytes"):
        try:
            df = pd.read_csv(io.BytesIO(result["file_bytes"]))
            return True, df
        except:
            return False, pd.DataFrame()
    return False, pd.DataFrame()

def to_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()


BASE_DIR = Path(__file__).resolve().parent

if "result_df" not in st.session_state:
    st.session_state.result_df = pd.DataFrame()
    st.session_state.result_ready = False

st.title("🛒 OMD Data - MegaMarket Crawler")

with st.sidebar:
    st.header("Cấu hình quét")
    auto_clean = st.checkbox("Tự động tối ưu từ khóa", value=True, 
                             help="Ví dụ: 'HAO TOMCHUACAY 67G*24' -> 'Hao tomchuacay'")
    delay_time = st.slider("Thời gian nghỉ giữa mỗi lần quét (giây)", 0.5, 5.0, 1.5)

with st.container(border=True):
    tab1, tab2 = st.tabs(["Nhập sản phẩm", "Upload file list sản phẩm (.txt, .csv)"])

    # TAB 1: NHẬP TAY
    with tab1:
        keyword_input = st.text_input("Nhập sản phẩm:", placeholder="VD: MI HAO HAO")
        if st.button("Bắt đầu quét", type="primary", key="btn_single"):
            search_kw = clean_input(keyword_input) if auto_clean else keyword_input
            with st.spinner(f"Đang tìm: {search_kw}..."):
                success, df = fetch_data(search_kw)
                if success:
                    st.session_state.result_df = df
                    st.session_state.result_ready = True
                    st.success(f"Tìm thấy {len(df)} sản phẩm cho '{search_kw}'")
                else:
                    st.error("Không có kết quả.")

    # TAB 2: UPLOAD FILE
    with tab2:
        uploaded_file = st.file_uploader("Chọn file", type=["txt", "csv"])
        if uploaded_file and st.button("Quét dữ liệu", type="primary"):
            content = uploaded_file.getvalue().decode("utf-8")
            raw_keywords = [l.strip() for l in content.splitlines() if l.strip()]
            
            all_dfs = []
            pbar = st.progress(0)
            status_text = st.empty()
            
            for i, raw_kw in enumerate(raw_keywords):
                search_kw = clean_input(raw_kw) if auto_clean else raw_kw
                status_text.text(f"Đang quét ({i+1}/{len(raw_keywords)}): {search_kw}")
                
                success, df = fetch_data(search_kw)
                if success:
                    all_dfs.append(df)
                
                pbar.progress((i + 1) / len(raw_keywords))
                time.sleep(delay_time)
            
            if all_dfs:
                st.session_state.result_df = pd.concat(all_dfs, ignore_index=True)
                st.session_state.result_ready = True
                st.success("Hoàn thành quét danh sách!")

# --- HIỂN THỊ KẾT QUẢ ---
if st.session_state.result_ready:
    df = st.session_state.result_df
    st.divider()
    
    st.subheader("👁️ Xem trước")
    st.dataframe(df, use_container_width=True, height=400)
    
    st.write("") 
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="📥 Tải CSV (UTF-8-SIG)", 
            data=df.to_csv(index=False).encode('utf-8-sig'), 
            file_name="result.csv", 
            mime="text/csv", 
            use_container_width=True
        )
    with col_dl2:
        st.download_button(
            label="📊 Tải Excel (.xlsx)", 
            data=to_excel(df), 
            file_name="result.xlsx", 
            use_container_width=True
        )
    
    st.divider()
    
    st.subheader("📊 Thống kê")
    st.metric("Tổng sản phẩm", len(df))