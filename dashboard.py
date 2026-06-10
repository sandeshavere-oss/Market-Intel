import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import csv
import sys
import re
from pathlib import Path
from datetime import datetime

# Import company matching logic
import sys
sys.path.append(str(Path(__file__).resolve().parent / "NEWS_ENGINE"))
import company_match

# Resolve database and mapping paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "DATABASE" / "market_intel.db"
MASTER_FILE = BASE_DIR / "MAPPINGS" / "company_master.csv"

# Configure page settings
st.set_page_config(
    page_title="Market Intel Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS for glassmorphism and modern dark styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Sleek gradient background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(9, 13, 26) 90%);
        color: #f1f5f9;
    }
    
    /* Header style */
    .main-header {
        background: linear-gradient(135deg, #8b5cf6, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Glassmorphic card styling */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }
    
    .glass-card:hover {
        transform: translateY(-4px);
        border-color: rgba(139, 92, 246, 0.4);
        box-shadow: 0 10px 30px rgba(139, 92, 246, 0.1);
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 8px;
        margin-bottom: 8px;
    }
    
    .badge-positive {
        background: linear-gradient(135deg, #065f46, #059669);
        color: #ecfdf5;
    }
    
    .badge-negative {
        background: linear-gradient(135deg, #991b1b, #dc2626);
        color: #fef2f2;
    }
    
    .badge-neutral {
        background: linear-gradient(135deg, #374151, #4b5563);
        color: #f9fafb;
    }
    
    .badge-high {
        background: linear-gradient(135deg, #9a3412, #ea580c);
        color: #fff7ed;
    }
    
    .badge-medium {
        background: linear-gradient(135deg, #3730a3, #4f46e5);
        color: #e0e7ff;
    }
    
    .badge-low {
        background: linear-gradient(135deg, #065f46, #0d9488);
        color: #f0fdfa;
    }
    
    .badge-theme {
        background: linear-gradient(135deg, #6b21a8, #9333ea);
        color: #faf5ff;
    }
    
    .badge-source {
        background: #1e293b;
        color: #cbd5e1;
        border: 1px solid #334155;
    }
    
    /* Keyword tags */
    .keyword-tag {
        display: inline-block;
        background: rgba(59, 130, 246, 0.1);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.2);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    /* News Title Link */
    .news-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #f8fafc;
        text-decoration: none;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .news-title:hover {
        color: #a78bfa;
        text-decoration: none;
    }
    
    /* Metric styling */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 4rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Rule-based classifier to dynamically extract Sentiment and Impact
def infer_sentiment_and_impact(title, keywords_str):
    title_lower = title.lower()
    kw_lower = keywords_str.lower() if keywords_str else ""
    
    # Defaults
    sentiment = "neutral"
    impact = "medium"
    
    # Sentiment Keywords
    pos_words = ["gain", "rise", "jump", "surge", "soar", "profit", "growth", "approved", "up", "bull", "buy", "win", "high", "success", "expand", "positive"]
    neg_words = ["loss", "fall", "crash", "slump", "drop", "decline", "down", "bear", "sell", "debt", "investigate", "fine", "cut", "weak", "concern", "negative"]
    
    pos_score = sum(1 for w in pos_words if w in title_lower or w in kw_lower)
    neg_score = sum(1 for w in neg_words if w in title_lower or w in kw_lower)
    
    if pos_score > neg_score:
        sentiment = "positive"
    elif neg_score > pos_score:
        sentiment = "negative"
        
    # Impact Keywords
    high_words = ["billion", "crore", "lakh cr", "policy", "rate cut", "rate hike", "sebi", "rbi", "merger", "acquisition", "ipo", "crash", "surge", "historic", "record", "shares crash", "slumps"]
    medium_words = ["earnings", "quarter", "results", "announcement", "stake", "order", "contract", "launch", "deals"]
    
    high_score = sum(1.5 for w in high_words if w in title_lower or w in kw_lower)
    med_score = sum(1.0 for w in medium_words if w in title_lower or w in kw_lower)
    
    if high_score > 2.0:
        impact = "high"
    elif high_score + med_score > 0.5:
        impact = "medium"
    else:
        impact = "low"
        
    return sentiment, impact

@st.cache_data(ttl=60)
def load_all_news():
    if not DB_PATH.exists():
        return pd.DataFrame()
        
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT id, title, keywords, related_companies, theme, source, created_at, link 
        FROM keywords 
        ORDER BY id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Precompute sentiment and impact
    if not df.empty:
        sentiments = []
        impacts = []
        for _, row in df.iterrows():
            sent, imp = infer_sentiment_and_impact(row["title"], row["keywords"])
            sentiments.append(sent)
            impacts.append(imp)
        df["sentiment"] = sentiments
        df["impact"] = impacts
    
    return df

DB_CORP_PATH = BASE_DIR / "DATABASE" / "corporate_events.db"

@st.cache_data(ttl=60)
def load_corporate_events():
    if not DB_CORP_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
        
    conn = sqlite3.connect(DB_CORP_PATH)
    try:
        df_meetings = pd.read_sql_query("SELECT id, company_symbol, meeting_date, purpose, source, created_at FROM board_meetings ORDER BY id DESC", conn)
    except Exception:
        df_meetings = pd.DataFrame()
        
    try:
        df_results = pd.read_sql_query("SELECT id, company_symbol, quarter, financial_year, revenue, net_profit, outcome_summary, created_at FROM financial_results ORDER BY id DESC", conn)
    except Exception:
        df_results = pd.DataFrame()
        
    conn.close()
    return df_meetings, df_results

DB_TWITTER_PATH = BASE_DIR / "DATABASE" / "twitter_intel.db"

@st.cache_data(ttl=60)
def load_twitter_tweets():
    if not DB_TWITTER_PATH.exists():
        return pd.DataFrame()
        
    conn = sqlite3.connect(DB_TWITTER_PATH)
    try:
        df = pd.read_sql_query("SELECT id, twitter_handle, tweet_text, tweet_url, sentiment, impact, created_at FROM tweets ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_latest_daily_intelligence(date_str=None):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if date_str:
            cursor.execute("SELECT summary_date, top_themes, top_companies, important_events, raw_summary, created_at FROM daily_intelligence WHERE summary_date = ?", (date_str,))
        else:
            cursor.execute("SELECT summary_date, top_themes, top_companies, important_events, raw_summary, created_at FROM daily_intelligence ORDER BY summary_date DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "summary_date": row[0],
                "top_themes": row[1],
                "top_companies": row[2],
                "important_events": row[3],
                "raw_summary": row[4],
                "created_at": row[5]
            }
    except Exception as e:
        conn.close()
        st.error(f"Error loading daily intelligence: {e}")
    return None

@st.cache_data(ttl=60)
def load_available_intelligence_dates():
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT summary_date FROM daily_intelligence ORDER BY summary_date DESC")
        dates = [r[0] for r in cursor.fetchall()]
        conn.close()
        return dates
    except Exception:
        conn.close()
        return []

@st.cache_data(ttl=30)
def load_event_signals():
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("""
            SELECT s.id, s.company, s.signal_date, s.velocity, s.today_mentions, s.avg_mentions,
                   s.event_type, s.event_date, s.event_description, s.signal_strength,
                   p.price_at_signal, p.price_5d_later, p.price_10d_later, p.return_5d, p.return_10d, p.outcome
            FROM event_signals s
            LEFT JOIN signal_performance p ON s.id = p.signal_id
            ORDER BY s.id DESC
        """, conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def load_nifty_return_for_signal(company, sig_date):
    db_price_path = Path("DATABASE/price_data.db")
    if not db_price_path.exists():
        return None, None, None
    conn_price = sqlite3.connect(db_price_path)
    cursor = conn_price.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
    has_history = cursor.fetchone() is not None
    
    dates = []
    try:
        if has_history:
            cursor.execute("SELECT trade_date FROM price_history WHERE symbol = ? AND trade_date >= ? ORDER BY trade_date ASC LIMIT 6", (company, sig_date))
        else:
            cursor.execute("SELECT date FROM daily_prices WHERE symbol = ? AND date >= ? ORDER BY date ASC LIMIT 6", (company, sig_date))
        dates = [r[0] for r in cursor.fetchall()]
    except Exception:
        pass
    
    if len(dates) < 6:
        conn_price.close()
        return None, None, None
        
    date_at_signal = dates[0]
    date_5d = dates[5]
    
    nifty_at_signal = None
    nifty_5d = None
    try:
        if has_history:
            cursor.execute("SELECT close FROM price_history WHERE symbol = 'NIFTY50' AND trade_date = ?", (date_at_signal,))
            r = cursor.fetchone()
            if r: nifty_at_signal = r[0]
            cursor.execute("SELECT close FROM price_history WHERE symbol = 'NIFTY50' AND trade_date = ?", (date_5d,))
            r = cursor.fetchone()
            if r: nifty_5d = r[0]
        else:
            cursor.execute("SELECT close FROM daily_prices WHERE symbol = 'NIFTY50' AND date = ?", (date_at_signal,))
            r = cursor.fetchone()
            if r: nifty_at_signal = r[0]
            cursor.execute("SELECT close FROM daily_prices WHERE symbol = 'NIFTY50' AND date = ?", (date_5d,))
            r = cursor.fetchone()
            if r: nifty_5d = r[0]
    except Exception:
        pass
        
    conn_price.close()
    
    if nifty_at_signal and nifty_5d:
        nifty_ret = ((nifty_5d - nifty_at_signal) / nifty_at_signal) * 100
        return nifty_ret, date_at_signal, date_5d
    return None, None, None

@st.cache_data(ttl=30)
def load_company_velocities():
    from datetime import timedelta
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("""
            SELECT company, date, mentions
            FROM company_mentions
            ORDER BY date DESC
        """, conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
        
    latest_date = df["date"].max()
    df_latest = df[df["date"] == latest_date].copy()
    
    try:
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
        window_start = (latest_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        window_end = (latest_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        
        df_window = df[(df["date"] >= window_start) & (df["date"] <= window_end)]
        avgs = df_window.groupby("company")["mentions"].mean().reset_index(name="avg_mentions")
        
        merged = pd.merge(df_latest, avgs, on="company", how="left")
        merged["avg_mentions"] = merged["avg_mentions"].fillna(0.5)
        merged["velocity"] = merged["mentions"] / merged["avg_mentions"]
        merged = merged.sort_values(by="velocity", ascending=False)
        return merged
    except Exception:
        return df_latest

# Load master company list helper
@st.cache_data
def load_company_master():
    companies = []
    if MASTER_FILE.exists():
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("company_name"):
                        companies.append(row["company_name"].strip())
        except Exception as e:
            st.error(f"Error loading company master: {e}")
    return sorted(companies)

@st.cache_data
def load_company_symbol_map():
    symbol_map = {}
    if MASTER_FILE.exists():
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("company_name", "").strip()
                    symbol = row.get("symbol", "").strip()
                    if name and symbol:
                        symbol_map[name] = symbol
        except Exception as e:
            st.error(f"Error loading symbol map: {e}")
    return symbol_map

# ----------------- MAIN APP HEADER -----------------
st.markdown("<div class='main-header'>MARKET INTEL DASHBOARD</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>AI-Driven Intelligence Monitoring from Exchanges, Regulatory Boards & News Feeds</div>", unsafe_allow_html=True)

# Load data
df_news = load_all_news()
df_meetings, df_results = load_corporate_events()
df_tweets = load_twitter_tweets()
company_list = load_company_master()
symbol_map = load_company_symbol_map()

if df_news.empty:
    st.warning("⚠️ No data found in the SQLite database. Ensure the n8n ingestion workflow is running.")
    st.stop()

# ----------------- SIDEBAR FILTERS -----------------
st.sidebar.markdown("### 🔍 Filter Controls")

# Company selector (Autocomplete Selectbox)
selected_company = st.sidebar.selectbox(
    "🏢 Select Company",
    options=["All Companies"] + company_list,
    index=0
)

# Extract unique themes for filter
all_themes = set()
for t_str in df_news["theme"].dropna():
    if t_str.strip():
        all_themes.update([t.strip() for t in t_str.split("|") if t.strip()])
theme_list = sorted(list(all_themes))

selected_theme = st.sidebar.selectbox(
    "🏷️ Filter by Theme",
    options=["All Themes"] + theme_list,
    index=0
)

# Sentiment filter
selected_sentiment = st.sidebar.selectbox(
    "🎭 Filter by Sentiment",
    options=["All Sentiments", "positive", "negative", "neutral"],
    index=0
)

# Impact filter
selected_impact = st.sidebar.selectbox(
    "⚡ Filter by Impact",
    options=["All Impacts", "high", "medium", "low"],
    index=0
)

# Resolve target symbol for corporate events
target_symbol = None
if selected_company != "All Companies":
    target_symbol = symbol_map.get(selected_company)

# ----------------- MULTI-TAB NAVIGATION -----------------
tab_intel, tab_news, tab_tweets, tab_signals, tab_top_companies, tab_top_themes, tab_upcoming_events, tab_performance = st.tabs([
    "💡 Daily Intelligence Briefing",
    "📰 Market News Feed",
    "🐦 Social Pulse (Twitter Alpha)",
    "⚡ SIGNALS",
    "🏢 TOP COMPANIES",
    "📈 TOP THEMES",
    "📅 UPCOMING EVENTS",
    "📊 SIGNAL PERFORMANCE"
])

# ==================== TAB 0: DAILY INTELLIGENCE BRIEFING ====================
with tab_intel:
    st.markdown("### 💡 Executive Daily Briefing")
    intel_dates = load_available_intelligence_dates()
    if not intel_dates:
        st.info("No daily intelligence summaries generated yet. Run the Tier 3 analysis script to create one!")
    else:
        # Render a selector for historical briefing dates
        col_date, _ = st.columns([2, 5])
        with col_date:
            selected_intel_date = st.selectbox(
                "📅 Select Briefing Date",
                options=intel_dates,
                index=0
            )
        
        brief = load_latest_daily_intelligence(selected_intel_date)
        if brief:
            st.markdown(f"**Briefing Generated on:** {brief['created_at']}")
            
            # Display full Markdown summary
            st.markdown(
                f"""
                <div class='glass-card'>
                    {brief['raw_summary']}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Key statistics / highlighted sections in columns
            st.markdown("### 📊 Briefing Highlights")
            col_themes, col_companies, col_events = st.columns(3)
            with col_themes:
                st.markdown(
                    f"""
                    <div class='glass-card' style='height: 100%; min-height: 250px;'>
                        <h4 style='color: #a78bfa; margin-top:0;'>🏷️ Key Themes</h4>
                        <div style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>
                            {brief['top_themes'].replace(chr(10), '<br>')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_companies:
                st.markdown(
                    f"""
                    <div class='glass-card' style='height: 100%; min-height: 250px;'>
                        <h4 style='color: #60a5fa; margin-top:0;'>🏢 Mentions</h4>
                        <div style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>
                            {brief['top_companies'].replace(chr(10), '<br>')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with col_events:
                st.markdown(
                    f"""
                    <div class='glass-card' style='height: 100%; min-height: 250px;'>
                        <h4 style='color: #10b981; margin-top:0;'>⚡ Event Signals</h4>
                        <div style='color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;'>
                            {brief['important_events'].replace(chr(10), '<br>')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.error("Failed to load details for the selected briefing date.")

# ==================== TAB 1: NEWS FEED ====================
with tab_news:
    # Filter Data Logic for News Feed
    filtered_df = df_news.copy()

    # Apply Company search
    if selected_company != "All Companies":
        # Call company search logic from company_match
        matched_articles = company_match.search_news_by_company(selected_company)
        matched_ids = [a["id"] for a in matched_articles]
        filtered_df = filtered_df[filtered_df["id"].isin(matched_ids)]

    # Apply Theme filter
    if selected_theme != "All Themes":
        filtered_df = filtered_df[filtered_df["theme"].apply(
            lambda x: selected_theme in str(x).split("|") if pd.notna(x) else False
        )]

    # Apply Sentiment filter
    if selected_sentiment != "All Sentiments":
        filtered_df = filtered_df[filtered_df["sentiment"] == selected_sentiment]

    # Apply Impact filter
    if selected_impact != "All Impacts":
        filtered_df = filtered_df[filtered_df["impact"] == selected_impact]

    # Metric Panel
    total_articles = len(filtered_df)
    pos_articles = len(filtered_df[filtered_df["sentiment"] == "positive"])
    pos_percentage = int((pos_articles / total_articles * 100)) if total_articles > 0 else 0

    unique_companies_set = set()
    for c_str in filtered_df["related_companies"].dropna():
        if c_str.strip():
            unique_companies_set.update([c.strip() for c in c_str.split("|") if c.strip()])
    unique_cos_count = len(unique_companies_set)

    filtered_themes_set = set()
    for t_str in filtered_df["theme"].dropna():
        if t_str.strip():
            filtered_themes_set.update([t.strip() for t in t_str.split("|") if t.strip()])
    active_themes_count = len(filtered_themes_set)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class='glass-card' style='text-align: center;'>
                <div class='metric-value'>{total_articles}</div>
                <div class='metric-label'>Matching Articles</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class='glass-card' style='text-align: center;'>
                <div class='metric-value'>{unique_cos_count}</div>
                <div class='metric-label'>Companies Mentioned</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class='glass-card' style='text-align: center;'>
                <div class='metric-value'>{active_themes_count}</div>
                <div class='metric-label'>Active Themes</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class='glass-card' style='text-align: center;'>
                <div class='metric-value' style='background: linear-gradient(135deg, #10b981, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{pos_percentage}%</div>
                <div class='metric-label'>Positive News Share</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # Visualizations
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📊 Theme Ingestion Volume")
        theme_counts = {}
        for t_str in filtered_df["theme"].dropna():
            for t in t_str.split("|"):
                t = t.strip()
                if t:
                    theme_counts[t] = theme_counts.get(t, 0) + 1
                    
        if theme_counts:
            theme_df = pd.DataFrame(list(theme_counts.items()), columns=["Theme", "Count"]).sort_values(by="Count", ascending=True)
            fig = px.bar(
                theme_df, 
                y="Theme", 
                x="Count", 
                orientation="h",
                color="Count",
                color_continuous_scale=px.colors.sequential.Purples,
                labels={"Count": "Articles Count"}
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#cbd5e1',
                margin=dict(l=20, r=20, t=10, b=10),
                coloraxis_showscale=False,
                height=280
            )
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No theme details available to chart.")

    with chart_col2:
        st.markdown("### 📈 Ingestion Activity Timeline")
        filtered_df["parsed_date"] = pd.to_datetime(filtered_df["created_at"]).dt.date
        timeline_df = filtered_df.groupby("parsed_date").size().reset_index(name="Count")
        
        if not timeline_df.empty:
            fig = px.line(
                timeline_df, 
                x="parsed_date", 
                y="Count",
                labels={"parsed_date": "Date", "Count": "News Volume"}
            )
            fig.update_traces(line_color="#10b981", line_width=3)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#cbd5e1',
                margin=dict(l=20, r=20, t=10, b=10),
                height=280
            )
            fig.update_yaxes(gridcolor='rgba(255,255,255,0.05)')
            fig.update_xaxes(gridcolor='rgba(255,255,255,0.05)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timeline details available to chart.")

    # News Listing
    st.markdown("### 📰 Market Intelligence News Feed")
    if filtered_df.empty:
        st.info("No news matches the selected filters.")
    else:
        for idx, row in filtered_df.iterrows():
            sentiment = row["sentiment"]
            impact = row["impact"]
            link = row["link"]
            title = row["title"]
            source = row["source"]
            created_at = row["created_at"]
            themes = [t.strip() for t in str(row["theme"]).split("|") if t.strip()]
            companies = [c.strip() for c in str(row["related_companies"]).split("|") if c.strip()]
            keywords = [k.strip() for k in str(row["keywords"]).split(",") if k.strip()]
            
            badge_sent_class = f"badge-{sentiment}"
            badge_imp_class = f"badge-{impact}"
            
            badges_html = f"<span class='badge badge-source'>{source}</span>"
            badges_html += f"<span class='badge {badge_sent_class}'>{sentiment}</span>"
            badges_html += f"<span class='badge {badge_imp_class}'>{impact} impact</span>"
            for t in themes:
                badges_html += f"<span class='badge badge-theme'>{t}</span>"
                
            keywords_html = "".join([f"<span class='keyword-tag'>{kw}</span>" for kw in keywords[:10]])
            
            companies_text = ""
            if companies:
                companies_text = f"<div style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem;'><strong>🏢 Companies:</strong> "
                companies_text += ", ".join([f"<span style='color: #a78bfa;'>{c}</span>" for c in companies])
                companies_text += "</div>"
                
            href_attr = f"href='{link}' target='_blank'" if link and link != "None" else "style='pointer-events: none; cursor: default;'"
            
            st.markdown(
                f"""
                <div class='glass-card'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;'>
                        <div>{badges_html}</div>
                        <div style='color: #64748b; font-size: 0.85rem;'>⏱️ {created_at}</div>
                    </div>
                    <a class='news-title' {href_attr}>{title}</a>
                    {companies_text}
                    <div style='margin-top: 0.75rem; margin-bottom: 0.5rem;'>{keywords_html}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==================== TAB 2: CORPORATE EVENTS ====================
with tab_upcoming_events:
    # Filter board meetings & results
    f_meetings = df_meetings.copy()
    f_results = df_results.copy()
    
    if target_symbol:
        f_meetings = f_meetings[f_meetings["company_symbol"] == target_symbol]
        f_results = f_results[f_results["company_symbol"] == target_symbol]
        
    # Metrics
    tot_meetings = len(f_meetings)
    tot_results = len(f_results)
    
    # Calculate unique companies in this subset
    unique_event_cos = set()
    if not f_meetings.empty:
        unique_event_cos.update(f_meetings["company_symbol"].dropna().unique())
    if not f_results.empty:
        unique_event_cos.update(f_results["company_symbol"].dropna().unique())
        
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{tot_meetings}</div><div class='metric-label'>Board Meetings</div></div>", unsafe_allow_html=True)
    with m_col2:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{tot_results}</div><div class='metric-label'>Financial Disclosures</div></div>", unsafe_allow_html=True)
    with m_col3:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{len(unique_event_cos)}</div><div class='metric-label'>Companies Tracked</div></div>", unsafe_allow_html=True)
        
    # Columns layout
    events_col1, events_col2 = st.columns(2)
    
    with events_col1:
        st.markdown("### 📅 Upcoming & Recent Board Meetings")
        if f_meetings.empty:
            st.info("No board meetings found.")
        else:
            for idx, row in f_meetings.iterrows():
                symbol = row["company_symbol"]
                date = row["meeting_date"]
                purpose = row["purpose"]
                src = row["source"]
                created = row["created_at"]
                
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;'>
                            <div>
                                <span class='badge badge-theme'>{symbol}</span>
                                <span class='badge badge-source'>{src}</span>
                            </div>
                            <div style='color: #64748b; font-size: 0.85rem;'>⏱️ {created}</div>
                        </div>
                        <div style='font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.5rem;'>{purpose}</div>
                        <div style='color: #60a5fa; font-size: 0.95rem; font-weight: 600;'>📅 Scheduled Date: {date}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
    with events_col2:
        st.markdown("### 📊 Quarterly & Annual Financial Results")
        if f_results.empty:
            st.info("No financial results reported.")
        else:
            for idx, row in f_results.iterrows():
                symbol = row["company_symbol"]
                qtr = row["quarter"] or "N/A"
                fy = row["financial_year"] or "N/A"
                rev = row["revenue"]
                profit = row["net_profit"]
                summary = row["outcome_summary"]
                created = row["created_at"]
                
                # Format numbers
                rev_text = f"₹{rev:.2f} Cr" if rev is not None and rev > 0 else "N/A"
                profit_text = f"₹{profit:.2f} Cr" if profit is not None and profit > 0 else "N/A"
                
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;'>
                            <div>
                                <span class='badge badge-theme'>{symbol}</span>
                                <span class='badge badge-medium'>{qtr} {fy}</span>
                            </div>
                            <div style='color: #64748b; font-size: 0.85rem;'>⏱️ {created}</div>
                        </div>
                        <div style='font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 0.75rem;'>{summary}</div>
                        <div style='display: flex; gap: 2rem;'>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Revenue</div>
                                <div style='color: #3b82f6; font-size: 1.25rem; font-weight: 700;'>{rev_text}</div>
                            </div>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Net Profit</div>
                                <div style='color: #10b981; font-size: 1.25rem; font-weight: 700;'>{profit_text}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ==================== TAB 3: SOCIAL PULSE ====================
with tab_tweets:
    f_tweets = df_tweets.copy()
    
    # Filter by Company
    company_aliases = []
    if selected_company != "All Companies" and MASTER_FILE.exists():
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("company_name") == selected_company:
                        company_aliases = [selected_company.lower(), row.get("symbol", "").lower()]
                        aliases_raw = row.get("aliases", "")
                        if aliases_raw:
                            company_aliases.extend([a.strip().lower() for a in aliases_raw.split("|") if a.strip()])
                        break
        except Exception:
            pass
            
    if selected_company != "All Companies" and company_aliases:
        def contains_company(text):
            if not text:
                return False
            text_lower = text.lower()
            for alias in company_aliases:
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, text_lower):
                    return True
            return False
        f_tweets = f_tweets[f_tweets["tweet_text"].apply(contains_company)]
        
    # Filter by Sentiment
    if selected_sentiment != "All Sentiments":
        f_tweets = f_tweets[f_tweets["sentiment"].apply(lambda x: str(x).lower() == selected_sentiment.lower())]
        
    # Filter by Impact
    if selected_impact != "All Impacts":
        f_tweets = f_tweets[f_tweets["impact"].apply(lambda x: str(x).lower() == selected_impact.lower())]
        
    # Metrics
    tot_tweets = len(f_tweets)
    pos_tweets = len(f_tweets[f_tweets["sentiment"].apply(lambda x: str(x).lower() == "positive")]) if not f_tweets.empty else 0
    pos_share = int(pos_tweets / tot_tweets * 100) if tot_tweets > 0 else 0
    handles_count = f_tweets["twitter_handle"].nunique() if not f_tweets.empty else 0
    
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{tot_tweets}</div><div class='metric-label'>Total Tweets</div></div>", unsafe_allow_html=True)
    with t_col2:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='background: linear-gradient(135deg, #10b981, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{pos_share}%</div><div class='metric-label'>Positive Sentiment</div></div>", unsafe_allow_html=True)
    with t_col3:
        st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{handles_count}</div><div class='metric-label'>Handles Tracked</div></div>", unsafe_allow_html=True)
        
    # Render Twitter Feed
    st.markdown("### 🐦 Social Media Pulse Feed (Twitter Alpha)")
    if f_tweets.empty:
        st.info("No tweets found matching the selected filters.")
    else:
        for idx, row in f_tweets.iterrows():
            handle = row["twitter_handle"]
            text = row["tweet_text"]
            url = row["tweet_url"]
            sentiment = row["sentiment"] or "Neutral"
            impact = row["impact"] or "Low"
            created = row["created_at"]
            
            badge_sent_class = f"badge-{str(sentiment).lower()}"
            badge_imp_class = f"badge-{str(impact).lower()}"
            
            st.markdown(
                f"""
                <div class='glass-card'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;'>
                         <div>
                             <span class='badge' style='background: #1da1f2; color: white; border-radius: 4px; padding: 2px 6px; font-size: 0.8rem;'>@{handle}</span>
                             <span class='badge {badge_sent_class}'>{sentiment}</span>
                             <span class='badge {badge_imp_class}'>{impact} Impact</span>
                         </div>
                         <div style='color: #64748b; font-size: 0.85rem;'>⏱️ {created}</div>
                    </div>
                    <div style='font-size: 1.15rem; color: #f8fafc; margin-bottom: 0.75rem; line-height: 1.5;'>{text}</div>
                    <a href='{url}' target='_blank' style='color: #1da1f2; font-size: 0.85rem; text-decoration: none; font-weight: 600;'>🔗 View Tweet</a>
                </div>
                """,
                unsafe_allow_html=True
            )

with tab_signals:
    st.markdown("### ⚡ AI-Generated Event Signals (Convergence Layer)")
    df_sig = load_event_signals()
    
    if df_sig.empty:
        st.info("No convergence signals generated yet.")
    else:
        f_sig = df_sig.copy()
        if selected_company != "All Companies" and target_symbol:
            f_sig = f_sig[f_sig["company"] == target_symbol]
            
        if f_sig.empty:
            st.info("No signals found matching the selected company.")
        else:
            for idx, row in f_sig.iterrows():
                comp = row["company"]
                sig_date = row["signal_date"]
                vel = row["velocity"]
                today_m = row["today_mentions"]
                avg_m = row["avg_mentions"]
                ev_type = row["event_type"]
                ev_date = row["event_date"]
                ev_desc = row["event_description"]
                strength = row["signal_strength"]
                ret_5d = row["return_5d"]
                ret_10d = row["return_10d"]
                res = row["outcome"] or "PENDING"
                
                # Fetch Nifty return for this signal dynamically
                nifty_ret_5d, _, _ = load_nifty_return_for_signal(comp, sig_date)
                
                # Style result badge
                if res == "WIN":
                    res_badge = f"<span class='badge' style='background: #10b981; color: white;'>Win (Outperformed Market)</span>"
                elif res == "LOSS":
                    res_badge = f"<span class='badge' style='background: #ef4444; color: white;'>Loss (Underperformed Market)</span>"
                elif res == "NEUTRAL":
                    res_badge = f"<span class='badge' style='background: #6b7280; color: white;'>Neutral</span>"
                else:
                    res_badge = f"<span class='badge badge-neutral'>Pending</span>"
                    
                strength_badge = f"<span class='badge badge-high' style='font-size:0.8rem; background: linear-gradient(135deg, #ea580c, #f97316); color:white;'>{strength} Conviction</span>" if strength == "HIGH" else f"<span class='badge badge-medium' style='font-size:0.8rem; background: linear-gradient(135deg, #4f46e5, #6366f1); color:white;'>{strength} Conviction</span>"
                
                ret_text_5d = f"{ret_5d:+.2f}%" if pd.notna(ret_5d) else "N/A"
                nifty_text_5d = f"{nifty_ret_5d:+.2f}%" if nifty_ret_5d is not None else "N/A"
                outperf_text_5d = f"{(ret_5d - nifty_ret_5d):+.2f}%" if (pd.notna(ret_5d) and nifty_ret_5d is not None) else "N/A"
                
                st.markdown(
                    f"""
                    <div class='glass-card'>
                        <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;'>
                            <div>
                                <span class='badge badge-theme' style='font-size: 1rem; background: linear-gradient(135deg, #6b21a8, #9333ea); color: white; padding: 2px 8px; border-radius: 4px;'>{comp}</span>
                                {strength_badge}
                                {res_badge}
                            </div>
                            <div style='color: #64748b; font-size: 0.85rem;'>⏱️ Signal Date: {sig_date}</div>
                        </div>
                        <div style='color: #f8fafc; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;'>
                            Mention Spike ({vel:.2f}x) &amp; Upcoming {ev_type}
                        </div>
                        <div style='color: #cbd5e1; font-size: 0.95rem; margin-bottom: 0.75rem; border-left: 3px solid #6366f1; padding-left: 0.5rem;'>
                            <strong>Event details:</strong> {ev_desc} (Scheduled: {ev_date})
                        </div>
                        <div style='display: flex; gap: 2rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.5rem; margin-top: 0.5rem;'>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Today's Mentions</div>
                                <div style='color: #cbd5e1; font-size: 1.1rem; font-weight: 700;'>{today_m}</div>
                            </div>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>30D Avg Mentions</div>
                                <div style='color: #cbd5e1; font-size: 1.1rem; font-weight: 700;'>{avg_m:.2f}</div>
                            </div>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Stock 5D Return</div>
                                <div style='color: {"#10b981" if (ret_5d and ret_5d > 0) else "#ef4444" if (ret_5d and ret_5d < 0) else "#cbd5e1"}; font-size: 1.1rem; font-weight: 700;'>{ret_text_5d}</div>
                            </div>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Nifty 5D Return</div>
                                <div style='color: #cbd5e1; font-size: 1.1rem; font-weight: 700;'>{nifty_text_5d}</div>
                            </div>
                            <div>
                                <div style='color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;'>Outperformance</div>
                                <div style='color: {"#10b981" if (pd.notna(ret_5d) and nifty_ret_5d is not None and ret_5d > nifty_ret_5d) else "#ef4444" if (pd.notna(ret_5d) and nifty_ret_5d is not None and ret_5d < nifty_ret_5d) else "#cbd5e1"}; font-size: 1.1rem; font-weight: 700;'>{outperf_text_5d}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

with tab_top_companies:
    st.markdown("### 🏢 Top Mentioned Companies Leaderboard")
    col_lead, col_vel = st.columns([1, 1])
    
    with col_lead:
        st.markdown("#### 🏆 All-Time News Mentions")
        conn = sqlite3.connect(DB_PATH)
        try:
            df_leader = pd.read_sql_query("""
                SELECT company as Company, SUM(mentions) as "Total Mentions", MAX(date) as "Last Active"
                FROM company_mentions
                GROUP BY company
                ORDER BY "Total Mentions" DESC
                LIMIT 15
            """, conn)
            st.dataframe(df_leader, use_container_width=True, hide_index=True)
        except Exception:
            st.info("Leaderboard data unavailable.")
        conn.close()
        
    with col_vel:
        st.markdown("#### 🔥 Top Mention Velocities (Today)")
        df_vel = load_company_velocities()
        if df_vel.empty:
            st.info("No velocity data available.")
        else:
            for idx, row in df_vel.head(10).iterrows():
                comp_sym = row["company"]
                mentions = row["mentions"]
                avg_m = row["avg_mentions"]
                vel = row["velocity"]
                
                is_spike = vel > 2.5
                vel_color = "#ef4444" if is_spike else "#60a5fa"
                vel_bg = "rgba(239, 68, 68, 0.08)" if is_spike else "rgba(96, 165, 250, 0.04)"
                border_color = "rgba(239, 68, 68, 0.2)" if is_spike else "rgba(96, 165, 250, 0.1)"
                
                spike_badge = "<span style='background: #ef4444; color: white; font-size: 0.75rem; padding: 1px 6px; border-radius: 3px; font-weight: 600; margin-left: 6px;'>SPIKE</span>" if is_spike else ""
                
                st.markdown(
                    f"""
                    <div class='glass-card' style='background: {vel_bg}; border: 1px solid {border_color}; margin-bottom: 0.5rem;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <strong style='font-size: 1.1rem; color: #f8fafc;'>{comp_sym}</strong>
                                {spike_badge}
                            </div>
                            <div style='font-size: 1.25rem; font-weight: 700; color: {vel_color};'>
                                {vel:.2f}x
                            </div>
                        </div>
                        <div style='display: flex; justify-content: space-between; margin-top: 0.5rem; font-size: 0.85rem; color: #94a3b8;'>
                            <div>Mentions Today: <strong style='color: #cbd5e1;'>{mentions}</strong></div>
                            <div>30D Average: <strong style='color: #cbd5e1;'>{avg_m:.2f}</strong></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

with tab_top_themes:
    st.markdown("### 📈 Theme Momentum & Velocity (Theme Layer)")
    conn = sqlite3.connect(DB_PATH)
    try:
        df_tv = pd.read_sql_query("""
            SELECT theme, date, mentions_today, "7d_avg", "30d_avg", z_score
            FROM theme_velocity
            ORDER BY date DESC, z_score DESC
        """, conn)
    except Exception:
        df_tv = pd.DataFrame()
    conn.close()
    
    if df_tv.empty:
        st.info("No theme velocity data available. Run theme_velocity.py first.")
    else:
        latest_date = df_tv["date"].max()
        df_latest_tv = df_tv[df_tv["date"] == latest_date]
        
        st.markdown(f"**Latest Theme Rankings (Date: {latest_date})**")
        
        col_list, col_chart = st.columns([2, 3])
        
        with col_list:
            st.markdown("#### 🏆 Theme Spikes Leaderboard (Z-Score)")
            df_list_display = df_latest_tv[["theme", "mentions_today", "30d_avg", "z_score"]].rename(columns={
                "theme": "Theme",
                "mentions_today": "Mentions Today",
                "30d_avg": "30D Avg",
                "z_score": "Z-Score"
            })
            st.dataframe(df_list_display, use_container_width=True, hide_index=True)
            
        with col_chart:
            st.markdown("#### 📊 Theme Trends Line Chart")
            FROZEN_THEMES_LIST = [
                "AI", "Semiconductor", "Banking", "Capital Markets", "Energy", "Defence", "Pharma",
                "Digital Infrastructure", "Green Energy", "Telecom", "Space Economy", "Macro Economy",
                "Commodities", "Metals & Mining", "EV", "Technology"
            ]
            selected_chart_themes = st.multiselect(
                "Select Themes to Plot", 
                options=FROZEN_THEMES_LIST, 
                default=["AI", "Semiconductor", "Defence", "Green Energy"]
            )
            
            df_chart = df_tv[df_tv["theme"].isin(selected_chart_themes)]
            if not df_chart.empty:
                df_chart = df_chart.sort_values("date")
                fig = px.line(
                    df_chart, 
                    x="date", 
                    y="mentions_today", 
                    color="theme", 
                    title="Daily Theme Mentions Over Time",
                    markers=True
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f8fafc',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)')
                )
                st.plotly_chart(fig, use_container_width=True)

with tab_performance:
    st.markdown("### 📊 Convergence Signals Performance Analytics")
    
    conn = sqlite3.connect(DB_PATH)
    try:
        df_perf = pd.read_sql_query("""
            SELECT signal_id as "Signal ID", company as "Company", signal_date as "Signal Date",
                   price_at_signal as "Entry Price", price_5d_later as "Price 5D", price_10d_later as "Price 10D",
                   return_5d as "Return 5D", return_10d as "Return 10D", outcome as "Outcome"
            FROM signal_performance
            ORDER BY signal_date DESC
        """, conn)
    except Exception as e:
        df_perf = pd.DataFrame()
    conn.close()
    
    if df_perf.empty:
        st.info("No signal performance logs available. Run the validation engine to generate analytics.")
    else:
        # Calculate quantitative metrics
        total_signals = len(df_perf)
        completed_sigs = df_perf[df_perf["Outcome"].isin(["WIN", "LOSS", "NEUTRAL"])]
        total_completed = len(completed_sigs)
        
        wins = len(df_perf[df_perf["Outcome"] == "WIN"])
        losses = len(df_perf[df_perf["Outcome"] == "LOSS"])
        neutrals = len(df_perf[df_perf["Outcome"] == "NEUTRAL"])
        
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0.0
        avg_ret_5d = df_perf["Return 5D"].mean() if df_perf["Return 5D"].notna().any() else 0.0
        avg_ret_10d = df_perf["Return 10D"].mean() if df_perf["Return 10D"].notna().any() else 0.0
        
        # Best / Worst Signal resolution
        best_signal_str = "N/A"
        worst_signal_str = "N/A"
        
        valid_ret_5d = df_perf[df_perf["Return 5D"].notna()]
        if not valid_ret_5d.empty:
            best_idx = valid_ret_5d["Return 5D"].idxmax()
            best_row = valid_ret_5d.loc[best_idx]
            best_signal_str = f"{best_row['Company']} ({best_row['Signal Date']}): {best_row['Return 5D']:+.2f}%"
            
            worst_idx = valid_ret_5d["Return 5D"].idxmin()
            worst_row = valid_ret_5d.loc[worst_idx]
            worst_signal_str = f"{worst_row['Company']} ({worst_row['Signal Date']}): {worst_row['Return 5D']:+.2f}%"
            
        # Display Metrics Grid
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value'>{total_signals}</div><div class='metric-label'>Total Signals</div></div>", unsafe_allow_html=True)
        with col_m2:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='background: linear-gradient(135deg, #10b981, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{win_rate:.1f}%</div><div class='metric-label'>Win Rate %</div></div>", unsafe_allow_html=True)
        with col_m3:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='color: {'#10b981' if avg_ret_5d >= 0 else '#ef4444'};'>{avg_ret_5d:+.2f}%</div><div class='metric-label'>Average Return 5D</div></div>", unsafe_allow_html=True)
        with col_m4:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='color: {'#10b981' if avg_ret_10d >= 0 else '#ef4444'};'>{avg_ret_10d:+.2f}%</div><div class='metric-label'>Average Return 10D</div></div>", unsafe_allow_html=True)
            
        col_m5, col_m6, col_m7 = st.columns(3)
        with col_m5:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='color: #10b981;'>{wins}</div><div class='metric-label'>Wins</div></div>", unsafe_allow_html=True)
        with col_m6:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='color: #ef4444;'>{losses}</div><div class='metric-label'>Losses</div></div>", unsafe_allow_html=True)
        with col_m7:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div class='metric-value' style='color: #94a3b8;'>{neutrals}</div><div class='metric-label'>Neutral</div></div>", unsafe_allow_html=True)
            
        col_m8, col_m9 = st.columns(2)
        with col_m8:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div style='font-size: 1.4rem; font-weight: 700; color: #10b981; margin-bottom: 0.25rem;'>{best_signal_str}</div><div class='metric-label'>🏆 Best Signal (5D)</div></div>", unsafe_allow_html=True)
        with col_m9:
            st.markdown(f"<div class='glass-card' style='text-align: center;'><div style='font-size: 1.4rem; font-weight: 700; color: #ef4444; margin-bottom: 0.25rem;'>{worst_signal_str}</div><div class='metric-label'>💀 Worst Signal (5D)</div></div>", unsafe_allow_html=True)
            
        # Display Table
        st.markdown("### Recent Signal Results")
        
        # Format returns and prices for nice presentation
        df_table = df_perf.copy()
        df_table["Return 5D"] = df_table["Return 5D"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
        df_table["Return 10D"] = df_table["Return 10D"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")
        
        # Display only specified columns in table: Signal ID, Company, Signal Date, Return 5D, Return 10D, Outcome
        df_table_display = df_table[["Signal ID", "Company", "Signal Date", "Return 5D", "Return 10D", "Outcome"]]
        st.dataframe(df_table_display, use_container_width=True, hide_index=True)

# Footer
st.markdown("<div class='footer'>Market Intel MVP • Powered by n8n, Ollama Mistral:7b, and Streamlit</div>", unsafe_allow_html=True)
