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
        # シークレットから認証情報を取得
        try:
            # .streamlit/secrets.tomlからパスワードを読み込む
            correct_password = st.secrets["passwords"].get(username)
            if correct_password and correct_password == password:
                st.session_state.authenticated = True
                return True
            else:
                st.sidebar.error("ユーザー名またはパスワードが違います")
                return False
        except Exception as e:
            # シークレットが見つからない場合はハードコードされたパスワードを使用（開発用）
            # 本番環境ではこのコードは削除してください
            fallback_users = {
                "admin": "ebay2024", 
                "user1": "password1"
            }
            if username in fallback_users and fallback_users[username] == password:
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
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        df['出品日時'] = pd.to_datetime(df['出品日時'])
        df['価格'] = pd.to_numeric(df['価格'], errors='coerce')
        
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
    
    # カテゴリー分析
    category_counts = seller_df['カテゴリー'].value_counts()
    
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
                tab1, tab2, tab3, tab4 = st.tabs(["📊 基本情報", "💰 価格分析", "📦 商品リスト", "💾 データ保存"])
                
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
                            title="価格分布"
                        )
                        st.plotly_chart(fig)
                    
                    with col2:
                        # 価格帯別商品数
                        price_analysis = price_dist.value_counts().sort_index()
                        st.write("価格帯別商品数")
                        st.dataframe(price_analysis)
                
                with tab3:
                    # 商品リスト
                    st.dataframe(
                        seller_df[['商品名', '価格', 'カテゴリー', 'URL', '出品日時']]
                        .sort_values('価格', ascending=False)
                    )
                
                with tab4:
                    # データの保存（クラウド対応版）
                    st.subheader("分析結果をダウンロード")
                    
                    # Excelファイルのダウンロードリンク
                    excel_link = get_excel_download_link(seller_df, f"{selected_seller}_products.xlsx")
                    st.markdown(excel_link, unsafe_allow_html=True)
                    
                    # 分析結果のJSONダウンロードリンク
                    analysis_results = {
                        'basic_stats': stats,
                        'category_analysis': {str(k): float(v) for k, v in category_counts.items()},
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    json_link = get_json_download_link(analysis_results, f"{selected_seller}_analysis.json")
                    st.markdown(json_link, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
