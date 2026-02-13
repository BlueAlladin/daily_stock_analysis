# -*- coding: utf-8 -*-
"""
===================================
Streamlit Web UI
===================================

Streamlit-based web interface for the stock analysis system.
This file serves as the main entry point for Streamlit deployment.

Usage:
    streamlit run streamlit_app.py

Or for Streamlit Cloud:
    Set the main file path to: streamlit_app.py
"""

import os
import sys
from pathlib import Path

# Setup environment before importing other modules
from src.config import setup_env
setup_env()

# Proxy configuration - controlled via USE_PROXY environment variable, default off
# GitHub Actions environment automatically skips proxy configuration
if os.getenv("GITHUB_ACTIONS") != "true" and os.getenv("USE_PROXY", "false").lower() == "true":
    # Local development environment, enable proxy (can be configured in .env)
    proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    proxy_port = os.getenv("PROXY_PORT", "10809")
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import streamlit as st
import pandas as pd

from src.config import get_config, Config
from src.logging_config import setup_logging
from src.services.analysis_service import AnalysisService
from src.services.history_service import HistoryService
from src.services.stock_service import StockService
from src.services.system_config_service import SystemConfigService
from src.services.task_queue import get_task_queue, TaskStatus as TaskStatusEnum

# Configure logging
setup_logging(log_prefix="streamlit_ui", debug=False)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="股票智能分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.config = get_config()
    st.session_state.analysis_service = AnalysisService()
    st.session_state.history_service = HistoryService()
    st.session_state.stock_service = StockService()
    st.session_state.system_config_service = SystemConfigService()


def main():
    """Main Streamlit application"""
    
    # Sidebar navigation
    st.sidebar.title("📈 股票智能分析系统")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "导航",
        ["股票分析", "历史记录", "股票行情", "任务监控", "系统配置"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 系统信息")
    config = st.session_state.config
    st.sidebar.info(f"**运行模式**: Streamlit Web UI")
    
    # Main content area
    if page == "股票分析":
        show_analysis_page()
    elif page == "历史记录":
        show_history_page()
    elif page == "股票行情":
        show_stock_quote_page()
    elif page == "任务监控":
        show_task_monitor_page()
    elif page == "系统配置":
        show_config_page()


def show_analysis_page():
    """Stock analysis page"""
    st.title("📊 股票分析")
    st.markdown("触发 AI 智能分析，获取股票决策建议")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        stock_code = st.text_input(
            "股票代码",
            placeholder="例如: 600519, 00700, AAPL",
            help="支持 A股(600519)、港股(00700)、美股(AAPL)"
        )
    
    with col2:
        report_type = st.selectbox(
            "报告类型",
            ["detailed", "simple"],
            index=0,
            help="detailed: 完整报告, simple: 精简报告"
        )
    
    col3, col4 = st.columns(2)
    with col3:
        force_refresh = st.checkbox("强制刷新", value=False, help="忽略缓存，重新分析")
    with col4:
        send_notification = st.checkbox("发送通知", value=True, help="分析完成后发送推送通知")
    
    if st.button("开始分析", type="primary", use_container_width=True):
        if not stock_code:
            st.error("请输入股票代码")
            return
        
        with st.spinner(f"正在分析 {stock_code}..."):
            try:
                query_id = uuid.uuid4().hex
                result = st.session_state.analysis_service.analyze_stock(
                    stock_code=stock_code.strip(),
                    report_type=report_type,
                    force_refresh=force_refresh,
                    query_id=query_id,
                    send_notification=send_notification
                )
                
                if result:
                    st.success("分析完成！")
                    st.markdown("---")
                    
                    # Display analysis result
                    st.subheader(f"📈 {result.get('stock_name', 'N/A')} ({result.get('stock_code', 'N/A')})")
                    
                    if "report" in result:
                        report = result["report"]
                        if isinstance(report, dict):
                            # Display structured report
                            if "summary" in report:
                                st.markdown("### 📋 分析摘要")
                                st.info(report["summary"])
                            
                            if "operation_advice" in report:
                                st.markdown("### 💡 操作建议")
                                advice = report["operation_advice"]
                                if "买入" in advice:
                                    st.success(f"**{advice}**")
                                elif "卖出" in advice:
                                    st.error(f"**{advice}**")
                                else:
                                    st.warning(f"**{advice}**")
                            
                            if "sentiment_score" in report:
                                st.markdown("### 📊 情绪评分")
                                score = report["sentiment_score"]
                                st.progress(score / 100)
                                st.caption(f"评分: {score}/100")
                            
                            if "trend_prediction" in report:
                                st.markdown("### 🔮 趋势预测")
                                st.info(report["trend_prediction"])
                            
                            # Display full report text if available
                            if "full_report" in report:
                                st.markdown("### 📄 完整报告")
                                st.markdown(report["full_report"])
                        else:
                            # Display as markdown text
                            st.markdown(report)
                    
                    # Show query ID
                    st.caption(f"查询 ID: {query_id}")
                    
                else:
                    st.error("分析失败，请检查股票代码是否正确或查看日志")
                    
            except Exception as e:
                st.error(f"分析过程中发生错误: {str(e)}")
                logger.exception("Analysis error")


def show_history_page():
    """History records page"""
    st.title("📚 历史记录")
    st.markdown("查看历史分析记录")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stock_code_filter = st.text_input("股票代码筛选", placeholder="留空显示全部")
    
    with col2:
        days_back = st.selectbox("时间范围", [7, 30, 90, 180, 365], index=1)
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    with col3:
        page_size = st.selectbox("每页数量", [10, 20, 50, 100], index=1)
    
    if st.button("查询", type="primary"):
        with st.spinner("正在加载历史记录..."):
            try:
                result = st.session_state.history_service.get_history_list(
                    stock_code=stock_code_filter.strip() if stock_code_filter else None,
                    start_date=start_date,
                    page=1,
                    limit=page_size
                )
                
                if result and "items" in result and result["items"]:
                    st.success(f"找到 {result.get('total', 0)} 条记录")
                    
                    # Display as table
                    df_data = []
                    for item in result["items"]:
                        meta = item.get("meta", {})
                        df_data.append({
                            "股票代码": meta.get("stock_code", "N/A"),
                            "股票名称": meta.get("stock_name", "N/A"),
                            "分析时间": meta.get("created_at", "N/A"),
                            "操作建议": meta.get("operation_advice", "N/A"),
                            "情绪评分": meta.get("sentiment_score", "N/A"),
                        })
                    
                    if df_data:
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Show details for selected record
                        st.markdown("---")
                        st.subheader("📄 查看详细报告")
                        selected_idx = st.selectbox(
                            "选择记录",
                            range(len(result["items"])),
                            format_func=lambda x: f"{result['items'][x]['meta'].get('stock_name', 'N/A')} - {result['items'][x]['meta'].get('created_at', 'N/A')}"
                        )
                        
                        if selected_idx is not None:
                            selected_item = result["items"][selected_idx]
                            if "report" in selected_item:
                                st.markdown(selected_item["report"])
                else:
                    st.info("暂无历史记录")
                    
            except Exception as e:
                st.error(f"查询失败: {str(e)}")
                logger.exception("History query error")


def show_stock_quote_page():
    """Stock quote page"""
    st.title("💹 股票行情")
    st.markdown("查看实时股票行情数据")
    
    stock_code = st.text_input(
        "股票代码",
        placeholder="例如: 600519, 00700, AAPL",
        help="支持 A股、港股、美股"
    )
    
    if st.button("查询行情", type="primary"):
        if not stock_code:
            st.error("请输入股票代码")
            return
        
        with st.spinner(f"正在获取 {stock_code} 的行情数据..."):
            try:
                quote = st.session_state.stock_service.get_realtime_quote(stock_code.strip())
                
                if quote:
                    st.success("行情数据获取成功")
                    
                    # Display quote information
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("当前价", f"{quote.get('current_price', 'N/A')}")
                    with col2:
                        change = quote.get('change', 0)
                        change_pct = quote.get('change_percent', 0)
                        st.metric("涨跌", f"{change:.2f}", f"{change_pct:.2f}%")
                    with col3:
                        st.metric("今日开盘", f"{quote.get('open', 'N/A')}")
                    with col4:
                        st.metric("昨日收盘", f"{quote.get('prev_close', 'N/A')}")
                    
                    # Additional info
                    st.markdown("---")
                    col5, col6 = st.columns(2)
                    with col5:
                        st.markdown(f"**最高价**: {quote.get('high', 'N/A')}")
                        st.markdown(f"**最低价**: {quote.get('low', 'N/A')}")
                        st.markdown(f"**成交量**: {quote.get('volume', 'N/A')}")
                    with col6:
                        st.markdown(f"**成交额**: {quote.get('amount', 'N/A')}")
                        st.markdown(f"**换手率**: {quote.get('turnover_rate', 'N/A')}")
                    
                    # Historical data
                    if st.checkbox("显示历史K线数据"):
                        try:
                            history = st.session_state.stock_service.get_history_data(
                                stock_code.strip(),
                                period="daily",
                                days=30
                            )
                            if history and "data" in history and history["data"]:
                                df = pd.DataFrame(history["data"])
                                st.line_chart(df.set_index("date")["close"])
                        except Exception as e:
                            st.warning(f"获取历史数据失败: {str(e)}")
                else:
                    st.error("获取行情数据失败")
                    
            except Exception as e:
                st.error(f"查询失败: {str(e)}")
                logger.exception("Stock quote error")


def show_task_monitor_page():
    """Task monitoring page"""
    st.title("⚙️ 任务监控")
    st.markdown("监控分析任务执行状态")
    
    if st.button("刷新任务列表", type="primary"):
        st.rerun()
    
    try:
        task_queue = get_task_queue()
        tasks = task_queue.list_tasks(limit=50)
        
        if tasks:
            st.success(f"当前有 {len(tasks)} 个任务")
            
            # Group tasks by status
            status_groups = {}
            for task in tasks:
                status = task.get("status", "unknown")
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(task)
            
            # Display tasks by status
            for status, task_list in status_groups.items():
                with st.expander(f"{status} ({len(task_list)})", expanded=True):
                    for task in task_list:
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.text(f"股票: {task.get('stock_code', 'N/A')}")
                        with col2:
                            st.text(f"创建时间: {task.get('created_at', 'N/A')}")
                        with col3:
                            if task.get("status") == TaskStatusEnum.RUNNING:
                                st.warning("运行中")
                            elif task.get("status") == TaskStatusEnum.COMPLETED:
                                st.success("已完成")
                            elif task.get("status") == TaskStatusEnum.FAILED:
                                st.error("失败")
                            else:
                                st.info(task.get("status", "未知"))
        else:
            st.info("当前没有任务")
            
    except Exception as e:
        st.error(f"获取任务列表失败: {str(e)}")
        logger.exception("Task monitor error")


def show_config_page():
    """System configuration page"""
    st.title("⚙️ 系统配置")
    st.markdown("查看和管理系统配置")
    
    try:
        config_service = st.session_state.system_config_service
        config_data = config_service.get_config(include_schema=True)
        
        if config_data and "config" in config_data:
            config_dict = config_data["config"]
            
            st.markdown("### 当前配置")
            
            # Display configuration in sections
            sections = {
                "AI 配置": ["gemini_api_key", "openai_api_key", "openai_base_url", "openai_model"],
                "通知配置": ["wechat_webhook_url", "feishu_webhook_url", "telegram_bot_token"],
                "数据源配置": ["tushare_token", "tavily_api_keys", "serpapi_keys"],
                "股票配置": ["stock_list"],
            }
            
            for section_name, keys in sections.items():
                with st.expander(section_name, expanded=False):
                    for key in keys:
                        if key in config_dict:
                            value = config_dict[key]
                            # Mask sensitive values
                            if "api_key" in key.lower() or "token" in key.lower() or "password" in key.lower():
                                display_value = f"{value[:8]}..." if value and len(value) > 8 else "***"
                            else:
                                display_value = value
                            st.text_input(key, value=display_value, disabled=True)
            
            st.info("⚠️ 配置修改需要在 .env 文件中进行，修改后需要重启应用")
        else:
            st.warning("无法加载配置信息")
            
    except Exception as e:
        st.error(f"加载配置失败: {str(e)}")
        logger.exception("Config page error")


if __name__ == "__main__":
    main()
