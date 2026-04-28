import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import io
import os

# 页面配置
st.set_page_config(page_title="人口趋势看板", layout="wide")

def process_nbs_file(filename):
    """专门解析国家统计局(NBS)那种奇怪格式的函数"""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 1. 过滤元数据（去掉前两行和末尾注释）
    data_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('数据库：', '时间：', '注：')):
            continue
        data_lines.append(line)
    
    # 2. 读取数据：核心在于 sep=',' 配合里面的 \t 清理
    cleaned_csv = "\n".join(data_lines)
    # NBS 导出的文件虽然叫 csv，但内容往往是用逗号分隔且带制表符的
    df = pd.read_csv(io.StringIO(cleaned_csv))
    
    # 3. 深度清理列名和内容
    df.columns = [c.replace('\t', '').strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')] # 删掉空列
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace('\t', '').str.strip()
            
    # 4. 逆透视：从“宽表”变“长表”，方便画图
    id_col = '指标'
    year_cols = [c for c in df.columns if '年' in c]
    
    df_long = df.melt(id_vars=[id_col], value_vars=year_cols, var_name='年份', value_name='数值')
    
    # 5. 清理数值
    df_long['年份'] = df_long['年份'].str.replace('年', '').astype(int)
    df_long['数值'] = pd.to_numeric(df_long['数值'], errors='coerce')
    df_long = df_long.dropna(subset=['数值'])
    df_long['来源'] = os.path.basename(filename)
    
    return df_long

# --- 网页主体 ---
st.title("📈 趋势数据自动追踪看板")

# 自动扫描 data 文件夹
data_files = glob.glob("data/*.csv")

if not data_files:
    st.info("💡 请在 data/ 文件夹中放入从统计局下载的 CSV 文件。")
else:
    # 加载并合并所有数据
    all_dfs = []
    for f in data_files:
        try:
            all_dfs.append(process_nbs_file(f))
        except Exception as e:
            st.error(f"解析 {f} 出错：{e}")
    
    if all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True)
        
        # 侧边栏：丝滑切换
        st.sidebar.header("控制面板")
        
        # 让用户选择指标（自动去重）
        target_indicator = st.sidebar.selectbox(
            "选择要追踪的指标", 
            options=sorted(full_df['指标'].unique())
        )
        
        # 过滤数据
        plot_df = full_df[full_df['指标'] == target_indicator].sort_values('年份')
        
        # 绘图
        if not plot_df.empty:
            fig = px.line(plot_df, x='年份', y='数值', 
                          markers=True, 
                          title=f"趋势追踪：{target_indicator}",
                          labels={"数值": "具体数值", "年份": "时间轴"},
                          template="plotly_dark") # 换个酷炫的深色主题
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 展示数据源
            st.caption(f"数据来源文件：{plot_df['来源'].unique().tolist()}")
            
            with st.expander("查看原始数据表"):
                st.dataframe(plot_df)