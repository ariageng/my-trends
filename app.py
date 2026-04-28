import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 页面设置
st.set_page_config(page_title="趋势动态看板", layout="wide")

# 1. 数据加载逻辑 (增加缓存机制，提升加载速度)
@st.cache_data
def load_data():
    df = pd.read_csv("data/population_data.csv")
    return df

try:
    df = load_data()
    
    # 2. 侧边栏：动态筛选器
    st.sidebar.title("🔍 数据维度追加")
    all_regions = df['region'].unique()
    selected_region = st.sidebar.selectbox("选择追踪地区", all_regions)
    
    # 3. 核心指标看板 (Metric)
    st.header(f"📈 {selected_region} 人口趋势监测")
    latest_val = df[df['region'] == selected_region]['value'].iloc[-1]
    st.metric(label="当前统计值", value=f"{latest_val} 万", delta="-2% (较去年)")

    # 4. 专业级图表构建
    sub_df = df[df['region'] == selected_region]
    
    fig = go.Figure()
    # 历史数据线
    hist = sub_df[sub_df['data_type'] == '历史']
    fig.add_trace(go.Scatter(x=hist['year'], y=hist['value'], name='历史数据', line=dict(color='#1f77b4', width=4)))
    
    # 预测数据线 (虚线)
    pred = sub_df[sub_df['data_type'] == '预测']
    fig.add_trace(go.Scatter(x=pred['year'], y=pred['value'], name='模型预测', line=dict(color='#1f77b4', width=4, dash='dot')))

    fig.update_layout(hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("数据加载失败，请检查 data/population_data.csv 格式")