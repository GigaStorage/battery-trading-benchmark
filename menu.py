import streamlit as st

GIGA_HOME_PAGE = "https://giga-storage.com/en/"
REPOSITORY_HOME_PAGE = "https://github.com/GigaStorage/battery-trading-benchmark"

def menu():
    st.sidebar.page_link("main.py", label="Battery Trading Benchmark")
    st.sidebar.write("## Blog Posts")
    st.sidebar.page_link("pages/blogpost_one.py", label="Blogpost One Dutch Dayahead Market")
