import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import json
from roblox_api import RobloxAPI

st.set_page_config(
    page_title="Roblox Expense Tracker",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0a0a0a;
        color: #ffffff;
    }
    .main {
        background-color: #0a0a0a;
    }
    div[data-testid="stMetricValue"] {
        font-size: 32px;
        color: #ffffff;
    }
    div[data-testid="stMetricLabel"] {
        color: #a0a0a0;
    }
    .stTextInput input {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #333333;
    }
    .stButton button {
        background-color: #8b5cf6;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
    }
    .stButton button:hover {
        background-color: #7c3aed;
    }
    h1, h2, h3, h4 {
        color: #ffffff !important;
    }
    .info-banner {
        background-color: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #a0a0a0;
    }
    .game-card {
        background-color: #1a1a1a;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border: 1px solid #2a2a2a;
    }
    div[data-testid="stDataFrame"] {
        background-color: #1a1a1a;
    }
    .stDataFrame {
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    if 'roblox_api' not in st.session_state:
        st.session_state.roblox_api = None
    if 'transactions' not in st.session_state:
        st.session_state.transactions = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'cookie_validated' not in st.session_state:
        st.session_state.cookie_validated = False
    if 'transactions_page' not in st.session_state:
        st.session_state.transactions_page = 0
    if 'date_range_start' not in st.session_state:
        st.session_state.date_range_start = None
    if 'date_range_end' not in st.session_state:
        st.session_state.date_range_end = None
    if 'overall_budget' not in st.session_state:
        st.session_state.overall_budget = None
    if 'monthly_budget' not in st.session_state:
        st.session_state.monthly_budget = None
    if 'budget_threshold' not in st.session_state:
        st.session_state.budget_threshold = 80
    if 'comparison_mode' not in st.session_state:
        st.session_state.comparison_mode = "Month vs Month"
    if 'cache_timestamp' not in st.session_state:
        st.session_state.cache_timestamp = None

def format_robux(amount):
    return f"{amount:,.0f} R$"

def is_cache_valid(cache_timestamp, expiry_minutes=30):
    if cache_timestamp is None:
        return False
    time_elapsed = datetime.now() - cache_timestamp
    return time_elapsed.total_seconds() < (expiry_minutes * 60)

def get_cache_age_text(cache_timestamp):
    if cache_timestamp is None:
        return "Never"
    
    time_elapsed = datetime.now() - cache_timestamp
    minutes = int(time_elapsed.total_seconds() / 60)
    
    if minutes < 1:
        seconds = int(time_elapsed.total_seconds())
        return f"{seconds} second{'s' if seconds != 1 else ''} ago"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        hours = int(minutes / 60)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

def create_spending_chart(df):
    category_spending = df.groupby('category')['amount'].sum().reset_index()
    category_spending = category_spending.sort_values('amount', ascending=False)
    
    total = category_spending['amount'].sum()
    category_spending['percentage'] = (category_spending['amount'] / total * 100).round(1)
    
    fig = go.Figure(data=[
        go.Bar(
            x=category_spending['category'],
            y=category_spending['amount'],
            marker_color='#8b5cf6',
            text=[f"{p}%" for p in category_spending['percentage']],
            textposition='outside',
            hovertemplate='%{x}<br>%{y:,.0f} R$<br>%{text}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        plot_bgcolor='#0a0a0a',
        paper_bgcolor='#0a0a0a',
        font_color='#ffffff',
        height=300,
        margin=dict(t=30, b=30, l=30, r=30),
        xaxis=dict(
            showgrid=False,
            color='#ffffff'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#2a2a2a',
            color='#ffffff'
        ),
        showlegend=False
    )
    
    return fig

def create_distribution_chart(df):
    category_spending = df.groupby('category')['amount'].sum().reset_index()
    total = category_spending['amount'].sum()
    category_spending['percentage'] = (category_spending['amount'] / total * 100).round(1)
    
    colors = ['#8b5cf6', '#6366f1', '#3b82f6', '#10b981', '#f59e0b']
    
    fig = go.Figure(data=[go.Pie(
        labels=category_spending['category'],
        values=category_spending['amount'],
        hole=0.6,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textfont=dict(color='#ffffff', size=12),
        hovertemplate='%{label}<br>%{value:,.0f} R$<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        plot_bgcolor='#0a0a0a',
        paper_bgcolor='#0a0a0a',
        font_color='#ffffff',
        height=300,
        margin=dict(t=30, b=30, l=30, r=30),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.1,
            font=dict(color='#ffffff')
        )
    )
    
    return fig

def create_spending_trend_chart(df):
    df_sorted = df.sort_values('date')
    df_sorted['cumulative'] = df_sorted['amount'].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_sorted['date'],
        y=df_sorted['cumulative'],
        mode='lines',
        line=dict(color='#8b5cf6', width=2),
        fill='tozeroy',
        fillcolor='rgba(139, 92, 246, 0.1)',
        name='Cumulative Spending',
        hovertemplate='%{x}<br>%{y:,.0f} R$<extra></extra>'
    ))
    
    fig.update_layout(
        plot_bgcolor='#0a0a0a',
        paper_bgcolor='#0a0a0a',
        font_color='#ffffff',
        height=300,
        margin=dict(t=30, b=30, l=30, r=30),
        xaxis=dict(
            showgrid=False,
            color='#ffffff'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#2a2a2a',
            color='#ffffff'
        ),
        showlegend=False
    )
    
    return fig

def create_comparison_chart(df1, df2, label1, label2):
    cat1 = df1.groupby('category')['amount'].sum().reset_index()
    cat2 = df2.groupby('category')['amount'].sum().reset_index()
    
    all_categories = list(set(cat1['category'].tolist() + cat2['category'].tolist()))
    
    amounts1 = []
    amounts2 = []
    
    for cat in all_categories:
        amt1 = cat1[cat1['category'] == cat]['amount'].values
        amt2 = cat2[cat2['category'] == cat]['amount'].values
        amounts1.append(amt1[0] if len(amt1) > 0 else 0)
        amounts2.append(amt2[0] if len(amt2) > 0 else 0)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name=label1,
        x=all_categories,
        y=amounts1,
        marker_color='#8b5cf6',
        hovertemplate='%{x}<br>%{y:,.0f} R$<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name=label2,
        x=all_categories,
        y=amounts2,
        marker_color='#3b82f6',
        hovertemplate='%{x}<br>%{y:,.0f} R$<extra></extra>'
    ))
    
    fig.update_layout(
        plot_bgcolor='#0a0a0a',
        paper_bgcolor='#0a0a0a',
        font_color='#ffffff',
        height=400,
        margin=dict(t=30, b=30, l=30, r=30),
        xaxis=dict(
            showgrid=False,
            color='#ffffff'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#2a2a2a',
            color='#ffffff',
            title='Robux Spent'
        ),
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#ffffff')
        )
    )
    
    return fig

def forecast_spending(monthly_spending_df, months_to_forecast=6):
    if len(monthly_spending_df) < 2:
        return None
    
    monthly_spending_df = monthly_spending_df.sort_values('month')
    
    x = np.arange(len(monthly_spending_df))
    y = monthly_spending_df['amount'].values
    
    coefficients = np.polyfit(x, y, 1)
    slope, intercept = coefficients
    
    future_x = np.arange(len(monthly_spending_df), len(monthly_spending_df) + months_to_forecast)
    future_y = slope * future_x + intercept
    future_y = np.maximum(future_y, 0)
    
    historical_trend = slope * x + intercept
    residuals = y - historical_trend
    std_dev = np.std(residuals)
    mean_residual = np.mean(np.abs(residuals))
    
    avg_spending = np.mean(y)
    if avg_spending > 0:
        variability = (std_dev / avg_spending) * 100
    else:
        variability = 0
    
    if variability < 20:
        confidence = "High"
        confidence_color = "#10b981"
    elif variability < 40:
        confidence = "Medium"
        confidence_color = "#f59e0b"
    else:
        confidence = "Low"
        confidence_color = "#ef4444"
    
    if slope > avg_spending * 0.05:
        trend = "Increasing"
        trend_icon = "↑"
        trend_color = "#ef4444"
    elif slope < -avg_spending * 0.05:
        trend = "Decreasing"
        trend_icon = "↓"
        trend_color = "#10b981"
    else:
        trend = "Stable"
        trend_icon = "—"
        trend_color = "#a0a0a0"
    
    last_month_spending = y[-1]
    if last_month_spending > 0:
        next_month_change = ((future_y[0] - last_month_spending) / last_month_spending) * 100
    else:
        next_month_change = 0
    
    return {
        'future_months': future_x,
        'future_spending': future_y,
        'trend': trend,
        'trend_icon': trend_icon,
        'trend_color': trend_color,
        'confidence': confidence,
        'confidence_color': confidence_color,
        'variability': variability,
        'slope': slope,
        'next_month_change': next_month_change
    }

def create_forecast_chart(monthly_spending_df, forecast_data, months_to_forecast=6):
    monthly_spending_df = monthly_spending_df.sort_values('month')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=monthly_spending_df['month'],
        y=monthly_spending_df['amount'],
        mode='lines+markers',
        name='Historical Spending',
        line=dict(color='#8b5cf6', width=3),
        marker=dict(size=8, color='#8b5cf6'),
        hovertemplate='%{x}<br>%{y:,.0f} R$<extra></extra>'
    ))
    
    last_historical_month = monthly_spending_df.iloc[-1]['month']
    last_historical_amount = monthly_spending_df.iloc[-1]['amount']
    
    from dateutil.relativedelta import relativedelta
    forecast_months = []
    current_date = pd.Period(last_historical_month, freq='M').to_timestamp()
    
    for i in range(months_to_forecast):
        current_date = current_date + relativedelta(months=1)
        forecast_months.append(pd.Period(current_date, freq='M'))
    
    forecast_x = [last_historical_month] + [str(m) for m in forecast_months]
    forecast_y = [last_historical_amount] + list(forecast_data['future_spending'])
    
    fig.add_trace(go.Scatter(
        x=forecast_x,
        y=forecast_y,
        mode='lines+markers',
        name='Predicted Spending',
        line=dict(color='#3b82f6', width=3, dash='dot'),
        marker=dict(size=8, color='#3b82f6', symbol='diamond'),
        hovertemplate='%{x}<br>%{y:,.0f} R$ (predicted)<extra></extra>'
    ))
    
    fig.update_layout(
        plot_bgcolor='#0a0a0a',
        paper_bgcolor='#0a0a0a',
        font_color='#ffffff',
        height=400,
        margin=dict(t=30, b=60, l=30, r=30),
        xaxis=dict(
            showgrid=False,
            color='#ffffff',
            title='Month'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#2a2a2a',
            color='#ffffff',
            title='Robux Spent'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#ffffff')
        ),
        hovermode='x unified'
    )
    
    return fig

init_session_state()

col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    st.markdown('<h1 style="text-align: center;">🎮 Roblox Expense Tracker</h1>', unsafe_allow_html=True)

if not st.session_state.cookie_validated:
    st.markdown('<div class="info-banner">🔒 <b>Private Data Analysis</b><br>This dashboard securely analyzes your Roblox spending data without storing information externally. All processing happens locally in your browser.</div>', unsafe_allow_html=True)
    
    st.markdown("### Enter Your Roblox Cookie")
    st.markdown("To fetch your transaction data, you need to provide your Roblox `.ROBLOSECURITY` cookie.")
    
    with st.expander("📖 How to get your Roblox cookie"):
        st.markdown("""
        1. Open Roblox.com in your browser
        2. Press F12 to open Developer Tools
        3. Go to the **Application** tab (Chrome) or **Storage** tab (Firefox)
        4. Click on **Cookies** → **https://www.roblox.com**
        5. Find `.ROBLOSECURITY` and copy its **Value**
        6. Paste it below
        
        ⚠️ **Warning**: Keep your cookie private! Never share it with anyone. This cookie gives full access to your account.
        """)
    
    cookie_input = st.text_input("Roblox Cookie (.ROBLOSECURITY)", type="password", placeholder="Enter your cookie here...")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔐 Authenticate", use_container_width=True):
            if cookie_input:
                with st.spinner("Validating cookie..."):
                    api = RobloxAPI(cookie_input)
                    if api.validate_cookie():
                        st.session_state.roblox_api = api
                        st.session_state.user_info = api.get_user_info()
                        st.session_state.cookie_validated = True
                        st.rerun()
                    else:
                        st.error("❌ Invalid cookie. Please check and try again.")
            else:
                st.warning("Please enter your cookie.")
else:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        cache_age = get_cache_age_text(st.session_state.cache_timestamp)
        cache_status = "🟢 Cached" if is_cache_valid(st.session_state.cache_timestamp) else "🔴 Expired" if st.session_state.cache_timestamp else "⚪ Not cached"
        st.markdown(f'<div class="info-banner">🔒 <b>Private Data Analysis</b><br>User ID: {st.session_state.user_info.get("id", "N/A")} | Last updated: {cache_age} | {cache_status}</div>', unsafe_allow_html=True)
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.transactions = None
            st.session_state.cache_timestamp = None
            st.success("♻️ Cache cleared! Fetching fresh data...")
            st.rerun()
    
    cache_valid = is_cache_valid(st.session_state.cache_timestamp)
    
    if st.session_state.transactions is None or not cache_valid:
        data_source = "cache (expired)" if st.session_state.cache_timestamp else "API (no cache)"
        if st.session_state.transactions is None:
            data_source = "API (forced refresh)"
        
        with st.spinner(f"Fetching transactions from {data_source}..."):
            raw_transactions = st.session_state.roblox_api.get_all_transactions(max_transactions=1000)
            if raw_transactions:
                st.session_state.transactions = st.session_state.roblox_api.parse_transactions(raw_transactions)
                st.session_state.cache_timestamp = datetime.now()
                st.info(f"✅ Loaded {len(st.session_state.transactions)} transactions from API. Cache valid for 30 minutes.")
            else:
                st.error("Unable to fetch transactions. Please try again.")
                st.stop()
    
    transactions = st.session_state.transactions
    
    if not transactions:
        st.info("No transactions found.")
        st.stop()
    
    df = pd.DataFrame(transactions)
    
    st.markdown("## 📅 Date Range Filter")
    
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    if st.session_state.date_range_start is None:
        st.session_state.date_range_start = min_date
    if st.session_state.date_range_end is None:
        st.session_state.date_range_end = max_date
    
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 2])
    
    with col1:
        if st.button("📅 Last 7 Days", use_container_width=True):
            st.session_state.date_range_start = (datetime.now() - timedelta(days=7)).date()
            st.session_state.date_range_end = max_date
            st.rerun()
    
    with col2:
        if st.button("📅 Last 30 Days", use_container_width=True):
            st.session_state.date_range_start = (datetime.now() - timedelta(days=30)).date()
            st.session_state.date_range_end = max_date
            st.rerun()
    
    with col3:
        if st.button("📅 Last 90 Days", use_container_width=True):
            st.session_state.date_range_start = (datetime.now() - timedelta(days=90)).date()
            st.session_state.date_range_end = max_date
            st.rerun()
    
    with col4:
        if st.button("📅 All Time", use_container_width=True):
            st.session_state.date_range_start = min_date
            st.session_state.date_range_end = max_date
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        from_date = st.date_input(
            "From Date",
            value=st.session_state.date_range_start,
            min_value=min_date,
            max_value=max_date,
            key="from_date_input"
        )
        if from_date != st.session_state.date_range_start:
            st.session_state.date_range_start = from_date
            st.rerun()
    
    with col2:
        to_date = st.date_input(
            "To Date",
            value=st.session_state.date_range_end,
            min_value=min_date,
            max_value=max_date,
            key="to_date_input"
        )
        if to_date != st.session_state.date_range_end:
            st.session_state.date_range_end = to_date
            st.rerun()
    
    df['date_only'] = df['date'].dt.date
    df = df[(df['date_only'] >= st.session_state.date_range_start) & (df['date_only'] <= st.session_state.date_range_end)]
    df = df.drop('date_only', axis=1)
    
    if len(df) == 0:
        st.warning("⚠️ No transactions found in the selected date range. Please adjust your filters.")
        st.stop()
    
    date_range_days = (st.session_state.date_range_end - st.session_state.date_range_start).days + 1
    cache_age = get_cache_age_text(st.session_state.cache_timestamp)
    is_cached = is_cache_valid(st.session_state.cache_timestamp)
    cache_indicator = "🟢 Using cached data" if is_cached else "🔴 Cache expired" if st.session_state.cache_timestamp else "⚪ No cache"
    
    st.markdown(f"""
    <div style="background-color: #1a1a1a; border-radius: 8px; padding: 16px; border: 1px solid #2a2a2a; margin-bottom: 20px;">
        <div style="color: #8b5cf6; font-weight: 600; font-size: 16px;">📊 Showing transactions from {st.session_state.date_range_start.strftime('%B %d, %Y')} to {st.session_state.date_range_end.strftime('%B %d, %Y')}</div>
        <div style="color: #a0a0a0; font-size: 14px; margin-top: 4px;">{date_range_days} days • {len(df):,} transactions • {format_robux(df['amount'].sum())} total spent</div>
        <div style="color: #666; font-size: 13px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #2a2a2a;">
            💾 {cache_indicator} • Last fetched: {cache_age} • Cache expires in: {30 - int((datetime.now() - st.session_state.cache_timestamp).total_seconds() / 60) if st.session_state.cache_timestamp and is_cached else 0} min
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💰 Budget Settings"):
        st.markdown("### Configure Your Spending Budgets")
        st.markdown("Set budget limits to track and manage your Robux spending.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            overall_budget_input = st.number_input(
                "Overall Budget Limit (Total Robux)",
                min_value=0,
                value=st.session_state.overall_budget if st.session_state.overall_budget else 0,
                step=100,
                help="Set your total spending budget for the selected date range"
            )
            if overall_budget_input > 0:
                st.session_state.overall_budget = overall_budget_input
            else:
                st.session_state.overall_budget = None
        
        with col2:
            monthly_budget_input = st.number_input(
                "Monthly Budget Limit (Robux per month)",
                min_value=0,
                value=st.session_state.monthly_budget if st.session_state.monthly_budget else 0,
                step=100,
                help="Set your monthly spending budget"
            )
            if monthly_budget_input > 0:
                st.session_state.monthly_budget = monthly_budget_input
            else:
                st.session_state.monthly_budget = None
        
        threshold_input = st.slider(
            "Budget Alert Threshold (%)",
            min_value=50,
            max_value=100,
            value=st.session_state.budget_threshold,
            step=5,
            help="Get warnings when spending reaches this percentage of your budget"
        )
        st.session_state.budget_threshold = threshold_input
        
        if st.session_state.overall_budget or st.session_state.monthly_budget:
            st.success(f"✅ Budget settings saved! Alerts will trigger at {st.session_state.budget_threshold}% of your budget.")
        else:
            st.info("💡 Set at least one budget limit to start tracking your spending goals.")
    
    st.markdown("## Total Spending Overview")
    
    total_spent = df['amount'].sum()
    
    df_sorted = df.sort_values('date')
    df_sorted['month'] = df_sorted['date'].dt.to_period('M').astype(str)
    current_month = datetime.now().strftime('%Y-%m')
    monthly_spending = df_sorted[df_sorted['month'] == current_month]['amount'].sum()
    
    if st.session_state.overall_budget or st.session_state.monthly_budget:
        if st.session_state.overall_budget:
            overall_percentage = (total_spent / st.session_state.overall_budget * 100) if st.session_state.overall_budget > 0 else 0
            overall_remaining = st.session_state.overall_budget - total_spent
            
            if overall_percentage < st.session_state.budget_threshold:
                overall_color = "#10b981"
                overall_status = "On Track"
                overall_icon = "✅"
            elif overall_percentage < 100:
                overall_color = "#f59e0b"
                overall_status = "Approaching Limit"
                overall_icon = "⚠️"
            else:
                overall_color = "#ef4444"
                overall_status = "Budget Exceeded"
                overall_icon = "🚨"
            
            st.markdown(f"""
            <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 2px solid {overall_color}; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <div style="color: #a0a0a0; font-size: 14px;">💎 Overall Budget Status</div>
                        <div style="color: #ffffff; font-size: 24px; font-weight: bold; margin-top: 4px;">{format_robux(total_spent)} / {format_robux(st.session_state.overall_budget)}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: {overall_color}; font-size: 18px; font-weight: bold;">{overall_icon} {overall_status}</div>
                        <div style="color: #a0a0a0; font-size: 14px; margin-top: 4px;">{overall_percentage:.1f}% used</div>
                    </div>
                </div>
                <div style="background-color: #2a2a2a; border-radius: 8px; height: 24px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, {overall_color}, {overall_color}); height: 100%; width: {min(overall_percentage, 100):.1f}%; transition: width 0.3s ease;"></div>
                </div>
                <div style="margin-top: 8px; color: #a0a0a0; font-size: 13px;">
                    {'Remaining: ' + format_robux(overall_remaining) if overall_remaining > 0 else 'Over budget by: ' + format_robux(abs(overall_remaining))}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if overall_percentage >= 100:
                st.error(f"🚨 **Budget Alert:** You've exceeded your overall budget by {format_robux(abs(overall_remaining))}!")
            elif overall_percentage >= st.session_state.budget_threshold:
                st.warning(f"⚠️ **Budget Warning:** You've used {overall_percentage:.1f}% of your overall budget. {format_robux(overall_remaining)} remaining.")
        
        if st.session_state.monthly_budget:
            monthly_percentage = (monthly_spending / st.session_state.monthly_budget * 100) if st.session_state.monthly_budget > 0 else 0
            monthly_remaining = st.session_state.monthly_budget - monthly_spending
            
            if monthly_percentage < st.session_state.budget_threshold:
                monthly_color = "#10b981"
                monthly_status = "On Track"
                monthly_icon = "✅"
            elif monthly_percentage < 100:
                monthly_color = "#f59e0b"
                monthly_status = "Approaching Limit"
                monthly_icon = "⚠️"
            else:
                monthly_color = "#ef4444"
                monthly_status = "Budget Exceeded"
                monthly_icon = "🚨"
            
            st.markdown(f"""
            <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 2px solid {monthly_color}; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <div style="color: #a0a0a0; font-size: 14px;">📅 Monthly Budget Status (Current Month)</div>
                        <div style="color: #ffffff; font-size: 24px; font-weight: bold; margin-top: 4px;">{format_robux(monthly_spending)} / {format_robux(st.session_state.monthly_budget)}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: {monthly_color}; font-size: 18px; font-weight: bold;">{monthly_icon} {monthly_status}</div>
                        <div style="color: #a0a0a0; font-size: 14px; margin-top: 4px;">{monthly_percentage:.1f}% used</div>
                    </div>
                </div>
                <div style="background-color: #2a2a2a; border-radius: 8px; height: 24px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, {monthly_color}, {monthly_color}); height: 100%; width: {min(monthly_percentage, 100):.1f}%; transition: width 0.3s ease;"></div>
                </div>
                <div style="margin-top: 8px; color: #a0a0a0; font-size: 13px;">
                    {'Remaining: ' + format_robux(monthly_remaining) if monthly_remaining > 0 else 'Over budget by: ' + format_robux(abs(monthly_remaining))}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if monthly_percentage >= 100:
                st.error(f"🚨 **Monthly Budget Alert:** You've exceeded your monthly budget by {format_robux(abs(monthly_remaining))}!")
            elif monthly_percentage >= st.session_state.budget_threshold:
                st.warning(f"⚠️ **Monthly Budget Warning:** You've used {monthly_percentage:.1f}% of your monthly budget. {format_robux(monthly_remaining)} remaining.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 24px; border: 1px solid #2a2a2a;">
            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">💎 Total Robux Spent</div>
            <div style="color: #8b5cf6; font-size: 36px; font-weight: bold;">{format_robux(total_spent)}</div>
            <div style="color: #666; font-size: 12px; margin-top: 4px;">Last updated: {datetime.now().strftime('%b %d, %Y')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        transaction_count = len(df)
        st.markdown(f"""
        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 24px; border: 1px solid #2a2a2a;">
            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">💳 Transaction Count</div>
            <div style="color: #3b82f6; font-size: 36px; font-weight: bold;">{transaction_count:,}</div>
            <div style="color: #666; font-size: 12px; margin-top: 4px;">Purchases tracked</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Spending by Category")
        fig_category = create_spending_chart(df)
        st.plotly_chart(fig_category, use_container_width=True)
    
    with col2:
        st.markdown("### Top Games")
        game_spending = df.groupby('item').agg({
            'amount': ['sum', 'count']
        }).reset_index()
        game_spending.columns = ['game', 'total_spent', 'purchases']
        game_spending = game_spending.sort_values('total_spent', ascending=False).head(5)
        
        total_all_games = df['amount'].sum()
        
        for idx, row in game_spending.iterrows():
            percentage = (row['total_spent'] / total_all_games * 100)
            st.markdown(f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #ffffff; font-weight: 600;">{row['game'][:40]}</div>
                        <div style="color: #666; font-size: 12px;">{int(row['purchases'])} purchases</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #8b5cf6; font-size: 18px; font-weight: bold;">{format_robux(row['total_spent'])}</div>
                        <div style="color: #666; font-size: 12px;">{percentage:.1f}% of total</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(game_spending) == 5:
            st.markdown(f'<div style="text-align: center; color: #666; margin-top: 12px; cursor: pointer;">View All Games ({df["item"].nunique()})</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("## Recent Transactions")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        category_filter = st.multiselect(
            "Filter by Category",
            options=df['category'].unique().tolist(),
            default=df['category'].unique().tolist()
        )
    
    df_filtered = df[df['category'].isin(category_filter)].sort_values('date', ascending=False)
    
    export_col1, export_col2, export_col3 = st.columns([1, 1, 3])
    
    with export_col1:
        csv_df = df_filtered.copy()
        csv_df['DATE'] = csv_df['date'].dt.strftime('%B %d, %Y')
        csv_df['ITEM'] = csv_df['item']
        csv_df['CATEGORY'] = csv_df['category']
        csv_df['SOURCE'] = csv_df['type']
        csv_df['AMOUNT'] = csv_df['amount'].apply(lambda x: f"-{int(x)} R$")
        csv_export = csv_df[['DATE', 'ITEM', 'CATEGORY', 'SOURCE', 'AMOUNT']].to_csv(index=False)
        
        st.download_button(
            label="📥 Export CSV",
            data=csv_export,
            file_name=f"roblox_transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with export_col2:
        json_df = df_filtered.copy()
        json_df['date'] = json_df['date'].dt.strftime('%B %d, %Y')
        json_data = json_df.to_dict(orient='records')
        json_export = json.dumps(json_data, indent=2)
        
        st.download_button(
            label="📥 Export JSON",
            data=json_export,
            file_name=f"roblox_transactions_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    items_per_page = 50
    total_pages = max(1, (len(df_filtered) - 1) // items_per_page + 1)
    
    if st.session_state.transactions_page >= total_pages:
        st.session_state.transactions_page = total_pages - 1
    
    start_idx = st.session_state.transactions_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(df_filtered))
    
    display_df = df_filtered.iloc[start_idx:end_idx].copy()
    display_df['formatted_date'] = display_df['date'].dt.strftime('%B %d, %Y')
    display_df['formatted_amount'] = display_df['amount'].apply(lambda x: f"-{int(x)} R$")
    
    table_df = display_df[['formatted_date', 'item', 'category', 'type', 'formatted_amount']].copy()
    table_df.columns = ['DATE', 'ITEM', 'CATEGORY', 'SOURCE', 'AMOUNT']
    
    st.dataframe(
        table_df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if st.session_state.transactions_page > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.transactions_page -= 1
                st.rerun()
    with col2:
        st.markdown(f'<div style="text-align: center; color: #666; padding: 8px;">Page {st.session_state.transactions_page + 1} of {total_pages}</div>', unsafe_allow_html=True)
    with col3:
        if st.session_state.transactions_page < total_pages - 1:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.transactions_page += 1
                st.rerun()
    
    st.markdown(f'<div style="text-align: center; color: #666; margin-top: 8px;">Showing {start_idx + 1}-{end_idx} of {len(df_filtered)} transactions</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("## Player Spending Analysis")
    
    tab1, tab2, tab3 = st.tabs(["All", "Players", "Groups"])
    
    with tab1:
        top_items = df.groupby('item')['amount'].sum().sort_values(ascending=False).head(10).reset_index()
        
        for idx, row in top_items.iterrows():
            item_transactions = len(df[df['item'] == row['item']])
            percentage = (row['amount'] / total_spent * 100)
            
            st.markdown(f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <div style="color: #ffffff; font-weight: 600; margin-bottom: 4px;">{row['item'][:50]}</div>
                        <div style="color: #666; font-size: 12px;">{item_transactions} transactions</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #8b5cf6; font-size: 18px; font-weight: bold;">{format_robux(row['amount'])}</div>
                        <div style="color: #666; font-size: 12px;">{percentage:.1f}%</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f'<div style="text-align: center; color: #666; margin-top: 12px;">View All {df["item"].nunique()} Recipients</div>', unsafe_allow_html=True)
    
    with tab2:
        df_sorted = df.sort_values('date')
        df_sorted['month'] = df_sorted['date'].dt.to_period('M').astype(str)
        monthly_spending = df_sorted.groupby('month')['amount'].sum().reset_index()
        
        if len(monthly_spending) > 0:
            st.markdown("### Spending Trend Over Time")
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly_spending['month'],
                y=monthly_spending['amount'],
                marker_color='#8b5cf6',
                hovertemplate='%{x}<br>%{y:,.0f} R$<extra></extra>'
            ))
            
            fig.update_layout(
                plot_bgcolor='#0a0a0a',
                paper_bgcolor='#0a0a0a',
                font_color='#ffffff',
                height=300,
                margin=dict(t=30, b=60, l=30, r=30),
                xaxis=dict(
                    showgrid=False,
                    color='#ffffff',
                    title='Month'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#2a2a2a',
                    color='#ffffff',
                    title='Robux Spent'
                ),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            avg_per_month = monthly_spending['amount'].mean()
            max_month = monthly_spending.loc[monthly_spending['amount'].idxmax()]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style="background-color: #1a1a1a; border-radius: 8px; padding: 16px; border: 1px solid #2a2a2a;">
                    <div style="color: #a0a0a0; font-size: 14px;">Average Monthly Spending</div>
                    <div style="color: #8b5cf6; font-size: 24px; font-weight: bold; margin-top: 8px;">{format_robux(avg_per_month)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background-color: #1a1a1a; border-radius: 8px; padding: 16px; border: 1px solid #2a2a2a;">
                    <div style="color: #a0a0a0; font-size: 14px;">Highest Spending Month</div>
                    <div style="color: #8b5cf6; font-size: 24px; font-weight: bold; margin-top: 8px;">{format_robux(max_month['amount'])}</div>
                    <div style="color: #666; font-size: 12px; margin-top: 4px;">{max_month['month']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🔮 Spending Forecast")
            st.markdown("Predictive analytics based on your historical spending patterns.")
            
            forecast_result = forecast_spending(monthly_spending, months_to_forecast=6)
            
            if forecast_result is None:
                st.info("📊 Insufficient data for forecasting. You need at least 2 months of transaction history to generate predictions.")
            else:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    next_month_pred = forecast_result['future_spending'][0]
                    change_icon = "↑" if forecast_result['next_month_change'] > 0 else "↓" if forecast_result['next_month_change'] < 0 else "—"
                    change_color = "#ef4444" if forecast_result['next_month_change'] > 0 else "#10b981" if forecast_result['next_month_change'] < 0 else "#a0a0a0"
                    
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">📅 Next Month Prediction</div>
                        <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">{format_robux(next_month_pred)}</div>
                        <div style="color: {change_color}; font-size: 14px; margin-top: 8px; font-weight: 600;">
                            {change_icon} {abs(forecast_result['next_month_change']):.1f}% vs last month
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    three_month_pred = np.sum(forecast_result['future_spending'][:3])
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">📊 Next 3 Months Total</div>
                        <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">{format_robux(three_month_pred)}</div>
                        <div style="color: #666; font-size: 14px; margin-top: 8px;">
                            Avg: {format_robux(three_month_pred / 3)}/month
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    six_month_pred = np.sum(forecast_result['future_spending'])
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">📈 Next 6 Months Total</div>
                        <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">{format_robux(six_month_pred)}</div>
                        <div style="color: #666; font-size: 14px; margin-top: 8px;">
                            Avg: {format_robux(six_month_pred / 6)}/month
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 2px solid {forecast_result['trend_color']};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="color: #a0a0a0; font-size: 14px;">Spending Trend</div>
                                <div style="color: {forecast_result['trend_color']}; font-size: 32px; font-weight: bold; margin-top: 8px;">
                                    {forecast_result['trend_icon']} {forecast_result['trend']}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 2px solid {forecast_result['confidence_color']};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="color: #a0a0a0; font-size: 14px;">Forecast Confidence</div>
                                <div style="color: {forecast_result['confidence_color']}; font-size: 32px; font-weight: bold; margin-top: 8px;">
                                    {forecast_result['confidence']}
                                </div>
                                <div style="color: #666; font-size: 12px; margin-top: 4px;">
                                    Variability: {forecast_result['variability']:.1f}%
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                fig_forecast = create_forecast_chart(monthly_spending, forecast_result, months_to_forecast=6)
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                st.markdown("""
                <div style="background-color: #1a1a1a; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; margin-top: 16px;">
                    <div style="color: #f59e0b; font-weight: 600; margin-bottom: 4px;">⚠️ Disclaimer</div>
                    <div style="color: #a0a0a0; font-size: 13px;">
                        Predictions are based on historical spending patterns using linear regression. Actual spending may vary due to changing habits, special events, or other factors. Use these forecasts as guidance, not guarantees.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align: center; color: #666; padding: 40px; background-color: #1a1a1a; border-radius: 8px;">No data available for spending trends.</div>', unsafe_allow_html=True)
    
    with tab3:
        game_category_df = df[df['category'] == 'Game']
        
        if len(game_category_df) > 0:
            st.markdown("### Game Purchases Analysis")
            
            game_type_spending = game_category_df.groupby('type')['amount'].sum().reset_index()
            game_type_spending = game_type_spending.sort_values('amount', ascending=False)
            
            total_game_spending = game_type_spending['amount'].sum()
            
            for idx, row in game_type_spending.iterrows():
                percentage = (row['amount'] / total_game_spending * 100) if total_game_spending > 0 else 0
                transaction_count = len(game_category_df[game_category_df['type'] == row['type']])
                
                st.markdown(f"""
                <div class="game-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="color: #ffffff; font-weight: 600; margin-bottom: 4px;">{row['type']}</div>
                            <div style="color: #666; font-size: 12px;">{transaction_count} purchases</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #8b5cf6; font-size: 18px; font-weight: bold;">{format_robux(row['amount'])}</div>
                            <div style="color: #666; font-size: 12px;">{percentage:.1f}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style="background-color: #1a1a1a; border-radius: 8px; padding: 16px; border: 1px solid #2a2a2a;">
                    <div style="color: #a0a0a0; font-size: 14px;">Total Game Spending</div>
                    <div style="color: #8b5cf6; font-size: 24px; font-weight: bold; margin-top: 8px;">{format_robux(total_game_spending)}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                avg_game_purchase = total_game_spending / len(game_category_df) if len(game_category_df) > 0 else 0
                st.markdown(f"""
                <div style="background-color: #1a1a1a; border-radius: 8px; padding: 16px; border: 1px solid #2a2a2a;">
                    <div style="color: #a0a0a0; font-size: 14px;">Avg per Game Purchase</div>
                    <div style="color: #8b5cf6; font-size: 24px; font-weight: bold; margin-top: 8px;">{format_robux(avg_game_purchase)}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            non_game_types = df['category'].value_counts().head(5)
            
            st.markdown("### Spending by Category Type")
            
            for category, count in non_game_types.items():
                category_amount = df[df['category'] == category]['amount'].sum()
                percentage = (category_amount / total_spent * 100) if total_spent > 0 else 0
                
                st.markdown(f"""
                <div class="game-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="color: #ffffff; font-weight: 600; margin-bottom: 4px;">{category}</div>
                            <div style="color: #666; font-size: 12px;">{count} transactions</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #8b5cf6; font-size: 18px; font-weight: bold;">{format_robux(category_amount)}</div>
                            <div style="color: #666; font-size: 12px;">{percentage:.1f}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("## Spending Distribution")
        fig_dist = create_distribution_chart(df)
        st.plotly_chart(fig_dist, use_container_width=True)
        
        category_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
        for category, amount in category_totals.items():
            percentage = (amount / total_spent * 100)
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2a2a2a;">
                <div style="color: #a0a0a0;">● {category}</div>
                <div>
                    <span style="color: #ffffff; font-weight: 600;">{format_robux(amount)}</span>
                    <span style="color: #666; margin-left: 12px;">{percentage:.1f}% of total</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("## Cosmetics Breakdown")
        
        cosmetics_df = df[df['category'] == 'Cosmetics']
        
        if len(cosmetics_df) > 0:
            cosmetics_total = cosmetics_df['amount'].sum()
            cosmetics_count = len(cosmetics_df)
            
            st.markdown(f"""
            <div style="background-color: #1a1a1a; border-radius: 12px; padding: 24px; border: 1px solid #2a2a2a; margin-bottom: 20px;">
                <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 8px;">Total Cosmetics Spending</div>
                <div style="color: #8b5cf6; font-size: 32px; font-weight: bold;">{format_robux(cosmetics_total)}</div>
                <div style="color: #666; font-size: 12px; margin-top: 4px;">{cosmetics_count} items purchased</div>
            </div>
            """, unsafe_allow_html=True)
            
            top_cosmetics = cosmetics_df.groupby('item')['amount'].sum().sort_values(ascending=False).head(5)
            
            for item, amount in top_cosmetics.items():
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #2a2a2a;">
                    <div style="color: #ffffff;">{item[:35]}</div>
                    <div style="color: #8b5cf6; font-weight: 600;">{format_robux(amount)}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align: center; color: #666; padding: 60px 20px; background-color: #1a1a1a; border-radius: 12px;">No cosmetic purchases found</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("## 📊 Period Comparison")
    st.markdown("Compare your spending across different time periods to identify trends and patterns.")
    
    comparison_mode = st.radio(
        "Select Comparison Mode",
        ["Month vs Month", "Week vs Week", "Custom Period"],
        horizontal=True,
        key="comparison_mode_selector"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_sorted = df.sort_values('date')
    df_sorted['month'] = df_sorted['date'].dt.to_period('M')
    df_sorted['week'] = df_sorted['date'].dt.to_period('W')
    
    if comparison_mode == "Month vs Month":
        available_months = sorted(df_sorted['month'].unique(), reverse=True)
        
        if len(available_months) < 2:
            st.info("📊 Not enough data for month comparison. You need transactions from at least 2 different months.")
        else:
            month_options = [str(m) for m in available_months]
            
            col1, col2 = st.columns(2)
            with col1:
                month1 = st.selectbox(
                    "Select First Month",
                    options=month_options,
                    index=0,
                    key="month1_selector"
                )
            
            with col2:
                month2 = st.selectbox(
                    "Select Second Month",
                    options=month_options,
                    index=min(1, len(month_options) - 1),
                    key="month2_selector"
                )
            
            if month1 and month2:
                df_month1 = df_sorted[df_sorted['month'] == pd.Period(month1)]
                df_month2 = df_sorted[df_sorted['month'] == pd.Period(month2)]
                
                if len(df_month1) == 0 or len(df_month2) == 0:
                    st.warning("⚠️ One or both selected months have no transaction data.")
                else:
                    total1 = df_month1['amount'].sum()
                    total2 = df_month2['amount'].sum()
                    count1 = len(df_month1)
                    count2 = len(df_month2)
                    avg1 = total1 / count1 if count1 > 0 else 0
                    avg2 = total2 / count2 if count2 > 0 else 0
                    
                    total_change = ((total2 - total1) / total1 * 100) if total1 > 0 else 0
                    count_change = ((count2 - count1) / count1 * 100) if count1 > 0 else 0
                    avg_change = ((avg2 - avg1) / avg1 * 100) if avg1 > 0 else 0
                    
                    def get_trend_indicator(change):
                        if change > 0:
                            return "↑", "#ef4444"
                        elif change < 0:
                            return "↓", "#10b981"
                        else:
                            return "—", "#a0a0a0"
                    
                    total_icon, total_color = get_trend_indicator(total_change)
                    count_icon, count_color = get_trend_indicator(count_change)
                    avg_icon, avg_color = get_trend_indicator(avg_change)
                    
                    st.markdown("### Comparison Summary")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💎 Total Spending</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(total1)}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(total2)}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {total_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {total_icon} {abs(total_change):.1f}% {('increase' if total_change > 0 else 'decrease') if total_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💳 Transaction Count</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{count1:,}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{count2:,}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {count_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {count_icon} {abs(count_change):.1f}% {('increase' if count_change > 0 else 'decrease') if count_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">📊 Avg per Transaction</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(avg1)}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{month2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(avg2)}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {avg_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {avg_icon} {abs(avg_change):.1f}% {('increase' if avg_change > 0 else 'decrease') if avg_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### Spending by Category Comparison")
                    
                    fig_comparison = create_comparison_chart(df_month1, df_month2, month1, month2)
                    st.plotly_chart(fig_comparison, use_container_width=True)
    
    elif comparison_mode == "Week vs Week":
        available_weeks = sorted(df_sorted['week'].unique(), reverse=True)
        
        if len(available_weeks) < 2:
            st.info("📊 Not enough data for week comparison. You need transactions from at least 2 different weeks.")
        else:
            week_options = [str(w) for w in available_weeks]
            
            col1, col2 = st.columns(2)
            with col1:
                week1 = st.selectbox(
                    "Select First Week",
                    options=week_options,
                    index=0,
                    key="week1_selector"
                )
            
            with col2:
                week2 = st.selectbox(
                    "Select Second Week",
                    options=week_options,
                    index=min(1, len(week_options) - 1),
                    key="week2_selector"
                )
            
            if week1 and week2:
                df_week1 = df_sorted[df_sorted['week'] == pd.Period(week1)]
                df_week2 = df_sorted[df_sorted['week'] == pd.Period(week2)]
                
                if len(df_week1) == 0 or len(df_week2) == 0:
                    st.warning("⚠️ One or both selected weeks have no transaction data.")
                else:
                    total1 = df_week1['amount'].sum()
                    total2 = df_week2['amount'].sum()
                    count1 = len(df_week1)
                    count2 = len(df_week2)
                    avg1 = total1 / count1 if count1 > 0 else 0
                    avg2 = total2 / count2 if count2 > 0 else 0
                    
                    total_change = ((total2 - total1) / total1 * 100) if total1 > 0 else 0
                    count_change = ((count2 - count1) / count1 * 100) if count1 > 0 else 0
                    avg_change = ((avg2 - avg1) / avg1 * 100) if avg1 > 0 else 0
                    
                    def get_trend_indicator(change):
                        if change > 0:
                            return "↑", "#ef4444"
                        elif change < 0:
                            return "↓", "#10b981"
                        else:
                            return "—", "#a0a0a0"
                    
                    total_icon, total_color = get_trend_indicator(total_change)
                    count_icon, count_color = get_trend_indicator(count_change)
                    avg_icon, avg_color = get_trend_indicator(avg_change)
                    
                    st.markdown("### Comparison Summary")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💎 Total Spending</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(total1)}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(total2)}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {total_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {total_icon} {abs(total_change):.1f}% {('increase' if total_change > 0 else 'decrease') if total_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💳 Transaction Count</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{count1:,}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{count2:,}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {count_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {count_icon} {abs(count_change):.1f}% {('increase' if count_change > 0 else 'decrease') if count_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col3:
                        st.markdown(f"""
                        <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                            <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">📊 Avg per Transaction</div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week1}</div>
                                    <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(avg1)}</div>
                                </div>
                                <div>
                                    <div style="color: #666; font-size: 12px;">{week2}</div>
                                    <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(avg2)}</div>
                                </div>
                            </div>
                            <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                            <div style="color: {avg_color}; font-size: 16px; font-weight: 600; text-align: center;">
                                {avg_icon} {abs(avg_change):.1f}% {('increase' if avg_change > 0 else 'decrease') if avg_change != 0 else 'no change'}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("### Spending by Category Comparison")
                    
                    fig_comparison = create_comparison_chart(df_week1, df_week2, week1, week2)
                    st.plotly_chart(fig_comparison, use_container_width=True)
    
    else:
        st.markdown("### Select Custom Date Ranges")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Period 1**")
            period1_col1, period1_col2 = st.columns(2)
            with period1_col1:
                period1_start = st.date_input(
                    "Start Date",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="period1_start"
                )
            with period1_col2:
                period1_end = st.date_input(
                    "End Date",
                    value=min(min_date + timedelta(days=30), max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="period1_end"
                )
        
        with col2:
            st.markdown("**Period 2**")
            period2_col1, period2_col2 = st.columns(2)
            with period2_col1:
                default_p2_start = min(min_date + timedelta(days=31), max_date)
                period2_start = st.date_input(
                    "Start Date",
                    value=default_p2_start,
                    min_value=min_date,
                    max_value=max_date,
                    key="period2_start"
                )
            with period2_col2:
                default_p2_end = min(min_date + timedelta(days=60), max_date)
                period2_end = st.date_input(
                    "End Date",
                    value=default_p2_end,
                    min_value=min_date,
                    max_value=max_date,
                    key="period2_end"
                )
        
        if period1_start > period1_end:
            st.error("⚠️ Period 1: Start date must be before end date.")
        elif period2_start > period2_end:
            st.error("⚠️ Period 2: Start date must be before end date.")
        else:
            df_period1 = df[(df['date'].dt.date >= period1_start) & (df['date'].dt.date <= period1_end)]
            df_period2 = df[(df['date'].dt.date >= period2_start) & (df['date'].dt.date <= period2_end)]
            
            if len(df_period1) == 0 or len(df_period2) == 0:
                st.warning("⚠️ One or both selected periods have no transaction data. Please adjust your date ranges.")
            else:
                total1 = df_period1['amount'].sum()
                total2 = df_period2['amount'].sum()
                count1 = len(df_period1)
                count2 = len(df_period2)
                avg1 = total1 / count1 if count1 > 0 else 0
                avg2 = total2 / count2 if count2 > 0 else 0
                
                total_change = ((total2 - total1) / total1 * 100) if total1 > 0 else 0
                count_change = ((count2 - count1) / count1 * 100) if count1 > 0 else 0
                avg_change = ((avg2 - avg1) / avg1 * 100) if avg1 > 0 else 0
                
                def get_trend_indicator(change):
                    if change > 0:
                        return "↑", "#ef4444"
                    elif change < 0:
                        return "↓", "#10b981"
                    else:
                        return "—", "#a0a0a0"
                
                total_icon, total_color = get_trend_indicator(total_change)
                count_icon, count_color = get_trend_indicator(count_change)
                avg_icon, avg_color = get_trend_indicator(avg_change)
                
                period1_label = f"{period1_start.strftime('%b %d')} - {period1_end.strftime('%b %d, %Y')}"
                period2_label = f"{period2_start.strftime('%b %d')} - {period2_end.strftime('%b %d, %Y')}"
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### Comparison Summary")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💎 Total Spending</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 1</div>
                                <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(total1)}</div>
                            </div>
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 2</div>
                                <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(total2)}</div>
                            </div>
                        </div>
                        <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                        <div style="color: {total_color}; font-size: 16px; font-weight: 600; text-align: center;">
                            {total_icon} {abs(total_change):.1f}% {('increase' if total_change > 0 else 'decrease') if total_change != 0 else 'no change'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">💳 Transaction Count</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 1</div>
                                <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{count1:,}</div>
                            </div>
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 2</div>
                                <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{count2:,}</div>
                            </div>
                        </div>
                        <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                        <div style="color: {count_color}; font-size: 16px; font-weight: 600; text-align: center;">
                            {count_icon} {abs(count_change):.1f}% {('increase' if count_change > 0 else 'decrease') if count_change != 0 else 'no change'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div style="background-color: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #2a2a2a;">
                        <div style="color: #a0a0a0; font-size: 14px; margin-bottom: 12px;">📊 Avg per Transaction</div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 1</div>
                                <div style="color: #8b5cf6; font-size: 20px; font-weight: bold;">{format_robux(avg1)}</div>
                            </div>
                            <div>
                                <div style="color: #666; font-size: 11px;">Period 2</div>
                                <div style="color: #3b82f6; font-size: 20px; font-weight: bold;">{format_robux(avg2)}</div>
                            </div>
                        </div>
                        <div style="background-color: #2a2a2a; height: 1px; margin: 12px 0;"></div>
                        <div style="color: {avg_color}; font-size: 16px; font-weight: 600; text-align: center;">
                            {avg_icon} {abs(avg_change):.1f}% {('increase' if avg_change > 0 else 'decrease') if avg_change != 0 else 'no change'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### Spending by Category Comparison")
                
                fig_comparison = create_comparison_chart(df_period1, df_period2, period1_label, period2_label)
                st.plotly_chart(fig_comparison, use_container_width=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f'<div style="text-align: center; color: #666; font-size: 12px;">Roblox Expense Tracker • Private Dashboard • Data provided by: Updated 0 days ago *</div>', unsafe_allow_html=True)
