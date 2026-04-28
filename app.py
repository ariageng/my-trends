import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import io
import os

# --- 页面配置 ---
st.set_page_config(page_title="高级趋势动态看板", layout="wide")
st.markdown("""<style> .main { background-color: #0e1117; } </style>""", unsafe_allow_html=True)

# --- 专家级数据清洗函数 ---
def nbs_cleaner(file_path):
    # 1. 自动识别编码并预读取
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='gb18030') as f:
            raw_lines = f.readlines()

    # 2. 精准定位数据区 (只保留包含逗号且不包含元数据的行)
    data_content = []
    for line in raw_lines:
        clean_line = line.strip().replace('\t', '') # 强制干掉制表符
        # 统计局数据行通常包含逗号，且不以特定字符开头
        if ',' in clean_line and not clean_line.startswith(('数据库', '时间', '注：')):
            data_content.append(clean_line)
    
    # 3. 构建初始 DataFrame
    csv_stream = io.StringIO("\n".join(data_content))
    df = pd.read_csv(csv_stream, sep=',').dropna(axis=1, how='all')
    
    # 4. 清洗列名 (去掉空格和"年"字)
    df.columns = [c.strip() for c in df.columns]
    
    # 5. 转换长表格式 (Tidy Data)
    id_vars = ['指标']
    value_vars = [c for c in df.columns if '年' in c]
    
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='年份', value_name='数值')
    
    # 6. 极致清洗数值
    df_long['年份'] = df_long['年份'].str.extract('(\d+)').astype(int)
    # 处理数值中的空格或逗号，并转为浮点数
    df_long['数值'] = pd.to_numeric(df_long['数值'].astype(str).str.replace(',', ''), errors='coerce')
    df_long = df_long.dropna(subset=['数值'])
    
    # 7. 标注来源
    df_long['来源文件'] = os.path.basename(file_path)
    return df_long

# --- 网页主体逻辑 ---
st.title("🛡️ 劳动市场与人口趋势追踪专家版")

# 自动扫描目录
data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

files = glob.glob(f"{data_dir}/*.csv")

if not files:
    st.warning("⚠️ 文件夹 data/ 中未发现 CSV 文件。请将下载的文件上传至该目录。")
else:
    # 加载所有数据并缓存以提高性能
    @st.cache_data
    def get_all_data(file_list):
        return pd.concat([nbs_cleaner(f) for f in file_list], ignore_index=True)

    try:
        full_data = get_all_data(files)
        
        # --- 侧边栏：丝滑筛选 ---
        st.sidebar.header("数据导航")
        
        # 智能指标搜索
        search_term = st.sidebar.text_input("🔍 搜索指标 (如: 总人口, 抚养比)", "")
        filtered_indicators = [i for i in full_data['指标'].unique() if search_term in i]
        
        selected_indicator = st.sidebar.selectbox(
            "选择具体追踪维度", 
            options=filtered_indicators if filtered_indicators else full_data['指标'].unique()
        )

        # --- 可视化核心区 ---
        target_df = full_data[full_data['指标'] == selected_indicator].sort_values('年份')
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig = px.line(
                target_df, x='年份', y='数值',
                markers=True, line_shape='linear',
                title=f"【{selected_indicator}】历史趋势分析",
                template="plotly_dark",
                color_discrete_sequence=['#00D4FF']
            )
            fig.update_traces(line_width=3, marker_size=10)
            fig.update_layout(hovermode="x unified", font=dict(family="Arial", size=14))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("关键统计数据")
            latest_year = target_df['年份'].max()
            latest_val = target_df[target_df['年份'] == latest_year]['数值'].values[0]
            st.metric(label=f"{latest_year}年数值", value=f"{latest_val:,.2f}")
            
            avg_val = target_df['数值'].mean()
            st.metric(label="历史平均水平", value=f"{avg_val:,.2f}")

        # 数据表查看
        with st.expander("📂 点击展开原始数据对账单"):
            st.table(target_df[['年份', '数值', '来源文件']])

    except Exception as e:
        st.error(f"🔴 数据处理流异常: {e}")
        st.info("提示：请检查 CSV 文件是否被损坏，或尝试重新从国家统计局下载。")