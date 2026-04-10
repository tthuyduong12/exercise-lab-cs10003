from pathlib import Path

import streamlit as st

from crawler_logic import crawl_products

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .st-emotion-cache-163ttbj {visibility: hidden;} 
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.set_page_config(
    page_title="Công Cụ Tra Cứu Sản Phẩm MegaMarket",
    page_icon="🛒",
    layout="centered",
)


BASE_DIR = Path(__file__).resolve().parent


def reset_result_state() -> None:
    st.session_state.result_ready = False
    st.session_state.result_name = ""
    st.session_state.result_bytes = b""


if "result_ready" not in st.session_state:
    reset_result_state()


st.markdown(
    """
    <style>
        .block-container {
            max-width: 760px;
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }
        .subtle-text {
            color: #4b5563;
            font-size: 0.95rem;
            margin-bottom: 1rem;
        }
        div[data-testid="stTextInput"] input {
            border-radius: 10px;
        }
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Công Cụ Tra Cứu Sản Phẩm MegaMarket")

with st.container(border=True):
    st.markdown(
        '<p class="subtle-text">Nhập từ khóa để quét dữ liệu sản phẩm và tải kết quả dưới dạng CSV.</p>',
        unsafe_allow_html=True,
    )

    keyword = st.text_input(
        "Nhập từ khóa tìm kiếm (ví dụ: Táo, Sữa, Thịt heo)...",
        placeholder="Ví dụ: bột ngọt",
    )

    if st.button("Bắt đầu quét dữ liệu", type="primary", use_container_width=True):
        reset_result_state()
        clean_keyword = keyword.strip()

        if not clean_keyword:
            st.error("Vui lòng nhập từ khóa trước khi bắt đầu.")
        else:
            with st.spinner("Đang thu thập dữ liệu từ MegaMarket, vui lòng đợi..."):
                result = crawl_products(clean_keyword, output_dir=BASE_DIR)

            if result["success"]:
                st.session_state.result_ready = True
                st.session_state.result_name = result["file_name"]
                st.session_state.result_bytes = result["file_bytes"]
                st.success("Đã hoàn thành! Bạn có thể tải file kết quả bên dưới.")
            else:
                st.error("Có lỗi xảy ra hoặc không tìm thấy sản phẩm. Vui lòng thử lại.")

    if st.session_state.result_ready:
        st.download_button(
            label="Tải kết quả (CSV)",
            data=st.session_state.result_bytes,
            file_name=st.session_state.result_name,
            mime="text/csv",
            use_container_width=True,
        )
