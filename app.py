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

# セキュリティ機能
def check_password():
    """パスワード認証を行う"""
    # 直接ハードコードされたパスワード
    users = {
        "admin": "ebay2024",  # 管理者用
        "user1": "password1",  # 追加ユーザー
        "ebay2024": "password1"  # 追加の組み合わせ
    }
    
    # セッション状態を確認
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    # サイドバーでユーザー名とパスワードを入力
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

# Streamlit設定（シンプルな設定）
st.set_page_config(
    page_title="eBay出品者分析",
    page_icon="📊",
    layout="wide"
)

def load_and_analyze_data(uploaded_file):
    """アップロードされたCSVファイルを分析"""
    try:
        # CSVファイルの読み込み
        try:
            # ヘッダーありの場合
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except:
            # ヘッダーなしの場合、ファイルを巻き戻してから再読み込み
            uploaded_file.seek(0)
            # 典型的なカラム名を定義
            columns = ['商品名', '価格', '価格（円）', '配送情報', '状態', '所在国', '出品者', '追加情報', '出品日時']
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig', header=None, names=columns)
        
        # データの前処理
        if '出品日時' in df.columns:
            df['出品日時'] = pd.to_datetime(df['出品日時'], errors='coerce')
        
        # 価格が複数列ある場合の対応
        if '価格' in df.columns:
            df['価格'] = pd.to_numeric(df['価格'], errors='coerce')
        elif '価格（円）' in df.columns:
            df['価格'] = pd.to_numeric(df['価格（円）'], errors='coerce')
        
        # 出品者情報の確認
        if '出品者' not in df.columns:
            st.warning("「出品者」列が見つかりません。データ形式を確認してください。")
            possible_seller_columns = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['seller', '出品者', 'セラー']):
                    possible_seller_columns.append(col)
            
            if possible_seller_columns:
                seller_col = st.selectbox("出品者情報の列を選択してください:", possible_seller_columns)
                df['出品者'] = df[seller_col]
        
        # 出品者リストの取得
        sellers = df['出品者'].value_counts()
        
        return df, sellers
    
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {str(e)}")
        return None, None

def analyze_seller(df, seller_name):
    """出品者の詳細分析"""
    seller_df = df[df['出品者'] == seller_name].copy()
    
    # 基本統計
    stats = {
        '総出品数': len(seller_df),
        '平均価格': seller_df['価格'].mean(),
        '最安値': seller_df['価格'].min(),
        '最高値': seller_df['価格'].max(),
        'フィードバック': seller_df['フィードバック'].iloc[0] if 'フィードバック' in seller_df.columns else 'N/A'
    }
    
    # カテゴリー分析（CSVファイルの列名に合わせて調整）
    category_column = None
    if 'カテゴリー' in seller_df.columns:
        category_column = 'カテゴリー'
    elif 'カテゴリ' in seller_df.columns:
        category_column = 'カテゴリ'
    elif 'Category' in seller_df.columns:
        category_column = 'Category'
    elif '状態' in seller_df.columns:  # 状態情報をカテゴリとして使用
        category_column = '状態'
    
    if category_column and not seller_df[category_column].isna().all():
        category_counts = seller_df[category_column].value_counts()
    else:
        # カテゴリー列がない場合はダミーデータを作成
        category_counts = pd.Series({'その他': len(seller_df)})
    
    # 価格帯分析
    price_ranges = [0, 10, 20, 30, 40, 50, 75, 100, float('inf')]
    price_labels = ['$0-10', '$10-20', '$20-30', '$30-40', '$40-50', '$50-75', '$75-100', '$100+']
    
    price_distribution = pd.cut(seller_df['価格'], 
                              bins=price_ranges,
                              labels=price_labels)
    
    return seller_df, stats, category_counts, price_distribution

def get_excel_download_link(df, filename="data.xlsx"):
    """エクセルファイルのダウンロードリンクを生成"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Excelファイルをダウンロード</a>'

def get_csv_download_link(df, filename="data.csv"):
    """CSVファイルのダウンロードリンクを生成"""
    csv = df.to_csv(index=False)
    csv_bytes = csv.encode('utf-8-sig')
    b64 = base64.b64encode(csv_bytes).decode()
    return f'<a href="data:text/csv;charset=utf-8,%EF%BB%BF{b64}" download="{filename}">CSVファイルをダウンロード</a>'

def get_json_download_link(data, filename="data.json"):
    """JSONファイルのダウンロードリンクを生成"""
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json_bytes = json_str.encode('utf-8')
    b64 = base64.b64encode(json_bytes).decode()
    return f'<a href="data:application/json;base64,{b64}" download="{filename}">JSON分析結果をダウンロード</a>'

def main():
    """メインアプリケーション"""
    # 認証チェック
    if not check_password():
        st.stop()  # 認証に失敗した場合は処理を停止
    
    st.title("eBay出品者分析 📊")
    
    # ファイルアップロード
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロード",
        type=['csv'],
        help="3_ebayフォルダのexportsから出力されたCSVファイルを選択してください"
    )
    
    if uploaded_file:
        # データの読み込みと分析
        df, sellers = load_and_analyze_data(uploaded_file)
        
        if df is not None:
            st.success(f"✅ {len(df)}件のデータを読み込みました")
            
            # データプレビュー
            with st.expander("データプレビュー（最初の5行）"):
                st.dataframe(df.head())
            
            # サイドバーに出品者選択を表示
            st.sidebar.header("出品者を選択")
            
            # 出品者情報の表示
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
                # 選択された出品者の分析
                seller_df, stats, category_counts, price_dist = analyze_seller(df, selected_seller)
                
                # タブで結果を表示
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 基本情報", "💰 価格分析", "📦 商品リスト", "💾 データ保存", "🔄 Amazon連携"])
                
                with tab1:
                    # 基本情報の表示
                    col1, col2 = st.columns(2)
                    with col1:
                        for key, value in stats.items():
                            if isinstance(value, float):
                                st.metric(key, f"${value:.2f}")
                            else:
                                st.metric(key, value)
                    
                    with col2:
                        # カテゴリー分布のグラフ
                        fig = px.pie(
                            values=category_counts.values,
                            names=category_counts.index,
                            title="カテゴリー分布"
                        )
                        st.plotly_chart(fig)
                
                with tab2:
                    # 価格分析
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 価格分布のヒストグラム
                        fig = px.histogram(
                            seller_df,
                            x='価格',
                            title="価格分布",
                            nbins=20
                        )
                        st.plotly_chart(fig)
                    
                    with col2:
                        # 価格帯別商品数
                        price_analysis = price_dist.value_counts().sort_index()
                        st.write("価格帯別商品数")
                        st.dataframe(price_analysis)
                        
                        # 箱ひげ図による価格の分布
                        fig = px.box(
                            seller_df,
                            y='価格',
                            title="価格の分布"
                        )
                        st.plotly_chart(fig)
                
                with tab3:
                    # 商品リスト（表示する列を動的に判断）
                    display_columns = []
                    for col in ['商品名', '価格', '価格（円）', 'カテゴリー', 'カテゴリ', 'Category', '状態', 'URL', '出品日時', '配送情報', '所在国']:
                        if col in seller_df.columns:
                            display_columns.append(col)
                    
                    if display_columns:
                        # 検索フィルター
                        search_term = st.text_input("商品名で検索:")
                        
                        filtered_df = seller_df
                        if search_term:
                            filtered_df = seller_df[seller_df['商品名'].str.contains(search_term, case=False, na=False)]
                        
                        st.dataframe(
                            filtered_df[display_columns].sort_values('価格', ascending=False)
                        )
                        
                        # 件数表示
                        st.info(f"表示中: {len(filtered_df)} / {len(seller_df)} 件")
                    else:
                        st.write("表示できる列がありません")
                
                with tab4:
                    # データの保存（クラウド対応版）
                    st.subheader("分析結果をダウンロード")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 商品データ")
                        # Excelファイルのダウンロードリンク
                        excel_link = get_excel_download_link(seller_df, f"{selected_seller}_products.xlsx")
                        st.markdown(excel_link, unsafe_allow_html=True)
                        
                        # CSVファイルのダウンロードリンク
                        csv_link = get_csv_download_link(seller_df, f"{selected_seller}_products.csv")
                        st.markdown(csv_link, unsafe_allow_html=True)
                    
                    with col2:
                        st.write("### 分析データ")
                        # 分析結果のJSONダウンロードリンク
                        analysis_results = {
                            'basic_stats': stats,
                            'category_analysis': {str(k): float(v) for k, v in category_counts.items()},
                            'price_distribution': {str(k): int(v) for k, v in price_dist.value_counts().items()},
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        json_link = get_json_download_link(analysis_results, f"{selected_seller}_analysis.json")
                        st.markdown(json_link, unsafe_allow_html=True)
                
                with tab5:
                    # Amazon連携機能
                    st.subheader("Amazon研究との連携")
                    
                    st.write("""
                    このセクションでは、eBayの商品データをAmazon研究ツールで活用するための準備ができます。
                    商品リストをダウンロードして、4_amazon_researchアプリケーションにインポートしてください。
                    """)
                    
                    # カスタムCSV形式のダウンロード（Amazon研究用）
                    if '商品名' in seller_df.columns and '価格' in seller_df.columns:
                        # Amazon研究用にデータを整形
                        amazon_df = seller_df.copy()
                        
                        # 必要な列を選択・名前変更
                        columns_to_select = []
                        amazon_columns = []
                        
                        # 商品名
                        if '商品名' in amazon_df.columns:
                            columns_to_select.append('商品名')
                            amazon_columns.append('product_name')
                        
                        # 価格
                        if '価格' in amazon_df.columns:
                            columns_to_select.append('価格')
                            amazon_columns.append('ebay_price')
                        
                        # カテゴリー
                        category_col = None
                        if 'カテゴリー' in amazon_df.columns:
                            category_col = 'カテゴリー'
                        elif 'カテゴリ' in amazon_df.columns:
                            category_col = 'カテゴリ'
                        elif 'Category' in amazon_df.columns:
                            category_col = 'Category'
                            
                        if category_col:
                            columns_to_select.append(category_col)
                            amazon_columns.append('category')
                        
                        # URL
                        if 'URL' in amazon_df.columns:
                            columns_to_select.append('URL')
                            amazon_columns.append('ebay_url')
                        
                        # その他の有用な情報
                        if '出品日時' in amazon_df.columns:
                            columns_to_select.append('出品日時')
                            amazon_columns.append('listing_date')
                        
                        if '状態' in amazon_df.columns:
                            columns_to_select.append('状態')
                            amazon_columns.append('condition')
                        
                        # 選択した列だけを抽出
                        if columns_to_select:
                            amazon_research_df = amazon_df[columns_to_select].copy()
                            amazon_research_df.columns = amazon_columns
                            
                            # ダウンロードリンクを生成
                            amazon_csv_link = get_csv_download_link(
                                amazon_research_df, 
                                f"{selected_seller}_for_amazon_research.csv"
                            )
                            st.markdown("### Amazon研究用データ")
                            st.markdown(amazon_csv_link, unsafe_allow_html=True)
                            
                            # データプレビュー
                            st.write("データプレビュー:")
                            st.dataframe(amazon_research_df.head())
                            
                            # 使い方の説明
                            st.info("""
                            **使用方法**:
                            1. 上記のCSVファイルをダウンロードします
                            2. 4_amazon_researchアプリを起動します
                            3. インポート機能からこのCSVをロードします
                            4. Amazonで商品を検索し、eBayの価格と比較します
                            """)
                    else:
                        st.warning("Amazon研究との連携に必要なデータ（商品名、価格など）が不足しています。")

if __name__ == "__main__":
    main()
