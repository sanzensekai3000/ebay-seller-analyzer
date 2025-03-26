"""
eBay出品者分析GUI アプリケーション
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime
import os
import base64
import io
import hmac
import chardet

# セキュリティ機能
def check_password():
    """パスワード認証を行う"""
    users = {
        "admin": "ebay2024",
        "user1": "password1",
        "ebay2024": "password1"
    }
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    st.sidebar.title("ログイン")
    username = st.sidebar.text_input("ユーザー名")
    password = st.sidebar.text_input("パスワード", type="password")
    
    if st.sidebar.button("ログイン"):
        if username in users and users[username] == password:
            st.session_state.authenticated = True
            return True
        else:
            st.sidebar.error("ユーザー名またはパスワードが違います")
            return False
    return False

# Streamlit設定
st.set_page_config(
    page_title="eBay出品者分析",
    page_icon="📊",
    layout="wide"
)

def detect_encoding(file_content):
    """ファイルのエンコーディングを検出"""
    result = chardet.detect(file_content)
    return result['encoding']

def load_and_analyze_data(uploaded_file):
    """アップロードされたCSVファイルを分析"""
    try:
        # ファイルの内容を読み込む
        file_content = uploaded_file.read()
        uploaded_file.seek(0)
        
        # エンコーディングを自動検出
        encoding = detect_encoding(file_content)
        st.write("検出されたエンコーディング:", encoding)
        
        # 複数のエンコーディングを試す
        encodings_to_try = ['utf-8-sig', 'cp932', 'shift-jis', 'utf-8', encoding]
        df = None
        error_messages = []
        
        for enc in encodings_to_try:
            if enc is None:
                continue
            try:
                uploaded_file.seek(0)
                # 最初に数行を読んでヘッダーを確認
                header_check = pd.read_csv(
                    uploaded_file,
                    encoding=enc,
                    nrows=5,
                    on_bad_lines='skip'
                )
                
                # ヘッダーの内容を確認
                st.write(f"エンコーディング {enc} でのヘッダー:", header_check.columns.tolist())
                
                uploaded_file.seek(0)
                # ヘッダーが正しく読み込めた場合、全データを読み込む
                df = pd.read_csv(
                    uploaded_file,
                    encoding=enc,
                    on_bad_lines='skip',
                    dtype=str  # 全ての列を一旦文字列として読み込む
                )
                st.success(f"✅ エンコーディング {enc} で読み込み成功")
                break
            except Exception as e:
                error_messages.append(f"エンコーディング {enc} での読み込み失敗: {str(e)}")
                continue

def analyze_seller(df, seller_name):
    """出品者の詳細分析"""
    seller_df = df[df['出品者'] == seller_name].copy()
    
    # 基本統計
    stats = {
        '総出品数': len(seller_df),
        '平均価格': seller_df['価格'].mean(),
        '最安値': seller_df['価格'].min(),
        '最高値': seller_df['価格'].max()
    }
    
    # カテゴリー分析
    category_column = None
    for col in ['カテゴリー', 'カテゴリ', 'Category', '状態']:
        if col in seller_df.columns:
            category_column = col
            break
    
    if category_column and not seller_df[category_column].isna().all():
        category_counts = seller_df[category_column].value_counts()
    else:
        category_counts = pd.Series({'その他': len(seller_df)})
    
    # 価格帯分析
    price_ranges = [0, 10, 20, 30, 40, 50, 75, 100, float('inf')]
    price_labels = ['$0-10', '$10-20', '$20-30', '$30-40', '$40-50', '$50-75', '$75-100', '$100+']
    
    price_distribution = pd.cut(seller_df['価格'], 
                              bins=price_ranges,
                              labels=price_labels)
    
    return seller_df, stats, category_counts, price_distribution
def prepare_download_data(df):
    """ダウンロード用にデータを準備"""
    # 日本語を含むデータを適切に処理
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
    return df

def main():
    """メインアプリケーション"""
    if not check_password():
        st.stop()
    
    st.title("eBay出品者分析 📊")
    
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロード",
        type=['csv'],
        help="3_ebayフォルダのexportsから出力されたCSVファイルを選択してください"
    )
    
    if uploaded_file:
        df, sellers = load_and_analyze_data(uploaded_file)
        
        if df is not None:
            st.success(f"✅ {len(df)}件のデータを読み込みました")
            
            with st.expander("データプレビュー（最初の5行）"):
                st.dataframe(df.head())
            
            st.sidebar.header("出品者を選択")
            
            seller_info = pd.DataFrame({
                '出品数': sellers,
                '平均価格': [df[df['出品者'] == seller]['価格'].mean() for seller in sellers.index]
            })
            
            st.sidebar.dataframe(seller_info)
            
            selected_seller = st.sidebar.selectbox(
                "分析する出品者を選択",
                sellers.index
            )
            
            if selected_seller:
                seller_df, stats, category_counts, price_dist = analyze_seller(df, selected_seller)
                
                tabs = st.tabs(["📊 基本情報", "💰 価格分析", "📦 商品リスト", "💾 データ保存", "🔄 Amazon連携"])
                
                with tabs[0]:
                    col1, col2 = st.columns(2)
                    with col1:
                        for key, value in stats.items():
                            if isinstance(value, float):
                                st.metric(key, f"${value:.2f}")
                            else:
                                st.metric(key, value)
                    
                    with col2:
                        fig = px.pie(
                            values=category_counts.values,
                            names=category_counts.index,
                            title="カテゴリー分布"
                        )
                        st.plotly_chart(fig)
                
                with tabs[1]:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.histogram(
                            seller_df,
                            x='価格',
                            title="価格分布",
                            nbins=20
                        )
                        st.plotly_chart(fig)
                    
                    with col2:
                        price_analysis = price_dist.value_counts().sort_index()
                        st.write("価格帯別商品数")
                        st.dataframe(price_analysis)
                        
                        fig = px.box(
                            seller_df,
                            y='価格',
                            title="価格の分布"
                        )
                        st.plotly_chart(fig)
                
                with tabs[2]:
                    display_columns = [col for col in ['商品名', '価格', 'カテゴリー', '状態', 'URL', '出品日時']
                                     if col in seller_df.columns]
                    
                    if display_columns:
                        search_term = st.text_input("商品名で検索:")
                        
                        filtered_df = seller_df
                        if search_term:
                            filtered_df = seller_df[seller_df['商品名'].str.contains(search_term, case=False, na=False)]
                        
                        st.dataframe(
                            filtered_df[display_columns].sort_values('価格', ascending=False)
                        )
                        
                        st.info(f"表示中: {len(filtered_df)} / {len(seller_df)} 件")
                    else:
                        st.write("表示できる列がありません")
                
                with tabs[3]:
                    st.subheader("分析結果をダウンロード")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 商品データ")
                        
                        # Excelファイルの準備
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            prepare_download_data(seller_df).to_excel(writer, index=False)
                        
                        st.download_button(
                            label="Excelファイルをダウンロード",
                            data=excel_buffer.getvalue(),
                            file_name=f"{selected_seller}_products.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # CSVファイルの準備
                        csv_data = prepare_download_data(seller_df).to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="CSVファイルをダウンロード",
                            data=csv_data,
                            file_name=f"{selected_seller}_products.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.write("### 分析データ")
                        
                        analysis_results = {
                            'basic_stats': stats,
                            'category_analysis': {str(k): float(v) for k, v in category_counts.items()},
                            'price_distribution': {str(k): int(v) for k, v in price_dist.value_counts().items()},
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        json_str = json.dumps(analysis_results, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="JSON分析結果をダウンロード",
                            data=json_str.encode('utf-8'),
                            file_name=f"{selected_seller}_analysis.json",
                            mime="application/json"
                        )
                
                with tabs[4]:
                    st.subheader("Amazon研究との連携")
                    
                    st.write("""
                    このセクションでは、eBayの商品データをAmazon研究ツールで活用するための準備ができます。
                    商品リストをダウンロードして、4_amazon_researchアプリケーションにインポートしてください。
                    """)
                    
                    if '商品名' in seller_df.columns and '価格' in seller_df.columns:
                        amazon_df = seller_df.copy()
                        
                        columns_mapping = {
                            '商品名': 'product_name',
                            '価格': 'ebay_price',
                            'カテゴリー': 'category',
                            'URL': 'ebay_url',
                            '出品日時': 'listing_date',
                            '状態': 'condition'
                        }
                        
                        # 存在する列のみを選択
                        columns_to_select = [col for col in columns_mapping.keys() if col in amazon_df.columns]
                        amazon_columns = [columns_mapping[col] for col in columns_to_select]
                        
                        if columns_to_select:
                            amazon_research_df = amazon_df[columns_to_select].copy()
                            amazon_research_df.columns = amazon_columns
                            
                            # CSVファイルの準備（UTF-8 with BOM）
                            csv_data = amazon_research_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="Amazon研究用CSVをダウンロード",
                                data=csv_data,
                                file_name=f"{selected_seller}_for_amazon_research.csv",
                                mime="text/csv"
                            )
                            
                            st.write("データプレビュー:")
                            st.dataframe(amazon_research_df.head())
                            
                            st.info("""
                            **使用方法**:
                            1. 上記のボタンでCSVファイルをダウンロードします
                            2. 4_amazon_researchアプリを起動します
                            3. インポート機能からこのCSVをロードします
                            4. Amazonで商品を検索し、eBayの価格と比較します
                            """)
                    else:
                        st.warning("Amazon研究との連携に必要なデータ（商品名、価格など）が不足しています。")

if __name__ == "__main__":
    main()
