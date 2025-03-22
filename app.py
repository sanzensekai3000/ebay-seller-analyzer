"""
シンプルなStreamlitアプリ
"""

import streamlit as st

st.title("eBay出品者分析ツール")
st.write("このアプリは正常に動作しています！")

# 簡単なデモ機能
if st.button("クリックしてください"):
    st.success("成功しました！アプリが正常に動作しています。") 