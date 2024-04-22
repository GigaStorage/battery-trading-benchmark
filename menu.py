import streamlit as st

# Links that are often reused on pages are stored and imported from here
GIGA_HOME_PAGE = "https://giga-storage.com/en/"
REPOSITORY_HOME_PAGE = "https://github.com/GigaStorage/battery-trading-benchmark"
ENTSOE_GITHUB_HOME_PAGE = "https://github.com/EnergieID/entsoe-py"


def menu():
    with st.sidebar:
        # Use Title Case when capitalizing labels: https://en.wikipedia.org/wiki/Title_case
        st.page_link("main.py", label="Battery Trading Benchmark")
        st.write("## Description")
        st.page_link("pages/description.py", label="Description Battery Trading Benchmark")
        st.write("## Blog Posts")
        st.page_link("pages/blogpost_one.py", label="Blogpost One Dutch Dayahead Market")
