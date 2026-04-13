import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="채권운용 Daily 주요 지표",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .main { background-color: #0d1117; }
    .stApp { background-color: #0d1117; }
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
        border: 1px solid #30363d; border-radius: 12px; padding: 16px 20px; margin: 4px 0;
    }
    .metric-label { color: #D9DADD; font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
    .metric-value { color: #e6edf3; font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
    .metric-delta-pos { color: #f85149; font-size: 15px; font-weight: 600; }
    .metric-delta-neg { color: #3fb950; font-size: 15px; font-weight: 600; }
    .metric-delta-zero { color: #8b949e; font-size: 15px; font-weight: 600; }
    .section-header {
        color: #e6edf3; font-size: 18px; font-weight: 700; letter-spacing: 0.04em;
        text-transform: uppercase; border-left: 4px solid #1f6feb; padding-left: 12px; margin: 24px 0 14px 0;
    }
    .header-main {
        background: linear-gradient(90deg, #161b22 0%, #0d1117 100%);
        border-bottom: 1px solid #21262d; padding: 16px 0 12px 0; margin-bottom: 24px;
    }
    .header-title { color: #e6edf3; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
    .header-sub { color: #8b949e; font-size: 12px; margin-top: 2px; }
    .date-badge {
        background: #1f6feb22; border: 1px solid #1f6feb55; border-radius: 20px;
        padding: 4px 14px; color: #58a6ff; font-size: 12px; font-weight: 500; display: inline-block;
    }
    .refresh-info { color: #484f58; font-size: 11px; text-align: right; }
    h1, h2, h3 { color: #e6edf3 !important; }
    .bond-table { width: 100%; border-collapse: collapse; font-size: 15px; }
    .bond-table th { background: #1f6feb33; color: #D9DADD; padding: 9px 14px; text-align: center; border: 1px solid #30363d; font-weight: 600; font-size: 15px; }
    .bond-table td { color: #c9d1d9; padding: 8px 14px; text-align: center; border: 1px solid #21262d; font-size: 15px; }
    .bond-table tr:nth-child(even) td { background: #161b22; }
    .bond-table tr:nth-child(odd) td { background: #0d1117; }
    .bond-table td:first-child { color: #D9DADD; font-weight: 500; text-align: left; }
    .td-pos { color: #f85149 !important; }
    .td-neg { color: #3fb950 !important; }
</style>
""", unsafe_allow_html=True)

SHEET_ID    = "1q26oZa4umx6ai1vLloVnCFWNTcsYhelay0AdToyd0Wc"
JSON_PATH   = "stream-dashboard-492904-e1298f3e3f92.json"
GRID_COLOR  = '#3d444d'
MINOR_COLOR = '#2a3038'

# ── 비밀번호 체크 ──────────────────────────────────────────────
def check_password():
    def password_entered():
        # Secrets 또는 하드코딩 둘 다 시도
        try:
            correct = st.secrets["password"]
        except:
            correct = "kyoboh02"
        if st.session_state["password"] == correct:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("""
            <div style='text-align:center; margin-bottom:20px;'>
                <div style='font-size:32px;'>📊</div>
                <div style='color:#e6edf3; font-size:18px; font-weight:700; margin:8px 0;'>채권운용 Daily 주요 지표</div>
                <div style='color:#8b949e; font-size:13px;'>접근 권한이 필요합니다</div>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("🔑 비밀번호", type="password",
                          on_change=password_entered, key="password",
                          placeholder="비밀번호를 입력하세요")
        return False
    elif not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("""
            <div style='text-align:center; margin-bottom:20px;'>
                <div style='font-size:32px;'>📊</div>
                <div style='color:#e6edf3; font-size:18px; font-weight:700; margin:8px 0;'>채권운용 Daily 주요 지표</div>
                <div style='color:#8b949e; font-size:13px;'>접근 권한이 필요합니다</div>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("🔑 비밀번호", type="password",
                          on_change=password_entered, key="password",
                          placeholder="비밀번호를 입력하세요")
            st.error("❌ 비밀번호가 틀렸습니다. 다시 시도해주세요.")
        return False
    return True

if not check_password():
    st.stop()

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    """로컬은 JSON 파일, Streamlit Cloud는 Secrets 사용"""
    try:
        # Streamlit Cloud Secrets 시도
        import json
        secret_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(secret_dict, scopes=SCOPES)
    except:
        # 로컬 JSON 파일 사용
        creds = Credentials.from_service_account_file(JSON_PATH, scopes=SCOPES)
    return creds

@st.cache_data(ttl=300)
def load_all_data():
    try:
        creds = get_credentials()
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SHEET_ID)
        data = {}
        for ws in spreadsheet.worksheets():
            records = ws.get_all_values()
            if records:
                df = pd.DataFrame(records)
                data[ws.title] = df
        return data
    except Exception as e:
        st.error(f"데이터 로딩 오류: {e}")
        return None

def grid_axis(nticks=12):
    return dict(
        gridcolor=GRID_COLOR, showgrid=True, zeroline=False, gridwidth=1,
        minor=dict(showgrid=True, gridcolor=MINOR_COLOR, gridwidth=1, nticks=5),
        nticks=nticks, tickfont=dict(color='#D9DADD', size=11),
    )

def base_layout(title, height=420):
    return dict(
        title=dict(text=title, font=dict(color='#e6edf3', size=16, family='Noto Sans KR'), x=0, y=0.99, yanchor='top'),
        paper_bgcolor='#161b22', plot_bgcolor='#161b22',
        font=dict(color='#8b949e', family='Noto Sans KR'),
        height=height, margin=dict(l=10, r=10, t=110, b=10),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.0, xanchor='left', x=0,
            font=dict(size=12, color='#D9DADD'), bgcolor='rgba(0,0,0,0)',
            tracegroupgap=0,
        ),
        hovermode='x unified',
        xaxis=grid_axis(), yaxis=grid_axis(10),
    )

# ── 파싱 함수들 ────────────────────────────────────────────────
def parse_spread(df):
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[0,1,2,3,4,5,6,7,10,11,12,13,14,15]].copy()
        rows.columns = ['일자','1Y','2Y','3Y','5Y','10Y','20Y','30Y','sp일자','2/3','3/10','5/30','10/30','20/30']
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        for c in ['1Y','2Y','3Y','5Y','10Y','20Y','30Y','2/3','3/10','5/30','10/30','20/30']:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        return rows.dropna(subset=['일자']).sort_values('일자')
    except:
        return pd.DataFrame()

def parse_irs(df):
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[0,1,2,3,4]].copy()
        rows.columns = ['일자','1Y','3Y','5Y','10Y']
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        for c in ['1Y','3Y','5Y','10Y']:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        return rows.dropna(subset=['일자']).sort_values('일자')
    except:
        return pd.DataFrame()

def parse_futures(df):
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[5,6,7,8,9,10,11]].copy()
        rows.columns = ['일자','3Y외국인','3Y증권선물','3Y은행','10Y외국인','10Y증권선물','10Y은행']
        # Google Sheets에서 오면 날짜가 문자열, 엑셀에서 오면 숫자(serial)
        def parse_date(val):
            try:
                num = float(val)
                return pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(num))
            except:
                return pd.to_datetime(val, errors='coerce')
        rows['일자'] = rows['일자'].apply(parse_date)
        for c in ['3Y외국인','3Y증권선물','3Y은행','10Y외국인','10Y증권선물','10Y은행']:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        return rows.dropna(subset=['일자']).sort_values('일자')
    except:
        return pd.DataFrame()

def parse_swap_ts(df):
    """Swap Time Series: 날짜 + 각 종목/만기별 컬럼으로 파싱"""
    try:
        cats_raw   = df.iloc[0, 1:].tolist()
        tenors_raw = df.iloc[1, 1:].tolist()
        # 카테고리 ffill — Google Sheets는 빈 셀이 '' 로 옴
        cats = []
        cur = None
        for c in cats_raw:
            if c is not None and str(c).strip() not in ['', 'nan', 'None']:
                cur = str(c).strip()
            cats.append(cur)
        # tenors도 빈 문자열 처리
        tenors_clean = [str(t).strip() if str(t).strip() not in ['', 'nan', 'None'] else 'X' for t in tenors_raw]
        col_names = ['일자'] + [f'{c}_{t}' for c, t in zip(cats, tenors_clean)]
        rows = df.iloc[2:].copy()
        rows = rows.iloc[:, :len(col_names)]
        rows.columns = col_names
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        for c in col_names[1:]:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        result = rows.dropna(subset=['일자']).sort_values('일자')
        return result
    except Exception as e:
        return pd.DataFrame()

def parse_bond_swap_static(df):
    try:
        tenors = ['1Y','1.5Y','2Y','3Y']
        records = []
        i = 2
        while i < len(df):
            label = df.iloc[i, 0]
            if pd.notna(label) and str(label).strip() not in ['', 'nan']:
                label = str(label).replace('\n', ' ')
                vals = [pd.to_numeric(df.iloc[i, j], errors='coerce') for j in range(1, 5)]
                chgs = [pd.to_numeric(df.iloc[i+1, j], errors='coerce') if i+1 < len(df) else None for j in range(1, 5)]
                records.append({'종목': label, 'vals': vals, 'chgs': chgs})
                i += 3
            else:
                i += 1
        return tenors, records
    except:
        return [], []

def delta_html(val, unit='bp'):
    try:
        v = float(val)
        if v > 0:   return f'<span class="metric-delta-pos">▲ {v:+.1f}{unit}</span>'
        elif v < 0: return f'<span class="metric-delta-neg">▼ {v:.1f}{unit}</span>'
        else:       return f'<span class="metric-delta-zero">─ 0{unit}</span>'
    except:
        return ''

def make_line_chart(df, x_col, y_cols, title, colors=None, height=420):
    default_colors = ['#58a6ff','#3fb950','#f0883e','#d2a8ff','#ffa198','#79c0ff','#ff7b72']
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        c = colors[i] if colors and i < len(colors) else default_colors[i % len(default_colors)]
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[col], name=col,
            line=dict(color=c, width=1.5),
            hovertemplate=f'<b>{col}</b>: %{{y:.4f}}<br>%{{x|%Y-%m-%d}}<extra></extra>'
        ))
    fig.update_layout(**base_layout(title, height))
    return fig

# ── 헤더 ──────────────────────────────────────────────────────
data = load_all_data()
today_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y년 %m월 %d일")

header_col, btn_col = st.columns([5, 1])
with header_col:
    st.markdown(f"""
<div class="header-main">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div class="header-title">📊 채권운용 Daily 주요 지표</div>
      <div class="header-sub">교보증권 FIS본부 채권운용부</div>
    </div>
    <div><div class="date-badge">📅 {today_str}</div></div>
  </div>
</div>""", unsafe_allow_html=True)
with btn_col:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if data is None:
    st.error("⚠️ Google Sheets 데이터를 불러올 수 없습니다. JSON 키 파일과 SHEET_ID를 확인하세요.")
    st.stop()

spread   = parse_spread(data.get('SPREAD', pd.DataFrame()))
irs      = parse_irs(data.get('IRS', pd.DataFrame()))
futures  = parse_futures(data.get('KTB Futures', pd.DataFrame()))
swap_ts  = parse_swap_ts(data.get('Swap Time Series', pd.DataFrame()))
static_tenors, bond_swap_static = parse_bond_swap_static(data.get('BOND SWAP', pd.DataFrame()))

# ══════════════════════════════════════════════════════════════
# 1. 국고채 금리
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🏛️ 국고채 금리 (KTB)</div>', unsafe_allow_html=True)

if not spread.empty:
    latest = spread.iloc[-1]
    prev   = spread.iloc[-2] if len(spread) > 1 else latest
    tenor_cols = ['2Y','3Y','5Y','10Y','20Y','30Y']
    metric_cols = st.columns(len(tenor_cols))
    for i, t in enumerate(tenor_cols):
        chg = (latest[t] - prev[t]) * 100
        with metric_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{t}</div>
                <div class="metric-value">{latest[t]:.3f}%</div>
                {delta_html(chg)}
            </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = make_line_chart(spread, '일자', ['3Y','5Y','10Y','20Y','30Y'],
                              '국고채 금리 추이')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        # 수익률 곡선: 현재 / 한달 전(edate-1) / 1년 전(edate-12)
        fig2 = go.Figure()
        x_axis = ['2Y','3Y','5Y','10Y','20Y','30Y']
        ref_date = latest['일자']
        one_month_ago = ref_date - pd.DateOffset(months=1)
        one_year_ago  = ref_date - pd.DateOffset(years=1)
        idx_1m = (spread['일자'] - one_month_ago).abs().idxmin()
        idx_1y = (spread['일자'] - one_year_ago).abs().idxmin()
        row_1m = spread.loc[idx_1m]
        row_1y = spread.loc[idx_1y]

        fig2.add_trace(go.Scatter(x=x_axis, y=[latest[t] for t in x_axis],
            mode='lines+markers', line=dict(color='#58a6ff', width=2),
            marker=dict(size=7), name='현재'))
        fig2.add_trace(go.Scatter(x=x_axis, y=[row_1m[t] for t in x_axis],
            mode='lines+markers', line=dict(color='#3fb950', width=1.5, dash='dash'),
            marker=dict(size=5), name=f'한달전 ({row_1m["일자"].strftime("%y.%m")})'))
        fig2.add_trace(go.Scatter(x=x_axis, y=[row_1y[t] for t in x_axis],
            mode='lines+markers', line=dict(color='#f0883e', width=1.5, dash='dot'),
            marker=dict(size=5), name=f'1년전 ({row_1y["일자"].strftime("%y.%m")})'))

        fig2.update_layout(**base_layout('수익률 곡선', height=420))
        fig2.update_layout(xaxis=grid_axis())
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 2. 스프레드 분석 — 카드 1x5 왼쪽, 각 스프레드별 개별 차트 오른쪽
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📐 스프레드 분석</div>', unsafe_allow_html=True)

if not spread.empty:
    latest_s = spread.iloc[-1]
    prev_s   = spread.iloc[-2] if len(spread) > 1 else latest_s
    sp_cols  = ['2/3','3/10','5/30','10/30','20/30']
    sp_colors = ['#58a6ff','#3fb950','#f0883e','#d2a8ff','#ffa198']

    card_col, chart_col = st.columns([1, 3])
    with card_col:
        for c in sp_cols:
            val = latest_s[c] * 100
            chg = (latest_s[c] - prev_s[c]) * 100
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Spread {c}</div>
                <div class="metric-value">{val:.1f}bp</div>
                {delta_html(chg)}
            </div>""", unsafe_allow_html=True)

    with chart_col:
        # 5개 개별 차트 — 각각 독립적으로 zoom/scale 가능
        sub = spread.copy()
        sub_bp = sub.copy()
        for c in sp_cols:
            sub_bp[c] = sub_bp[c] * 100

        # 2열 그리드로 배치
        chart_grid_rows = [
            st.columns(2),
            st.columns(2),
            st.columns(2),
        ]
        positions_grid = [(0,0),(0,1),(1,0),(1,1),(2,0)]
        for i, (c, color, pos) in enumerate(zip(sp_cols, sp_colors, positions_grid)):
            row_idx, col_idx = pos
            with chart_grid_rows[row_idx][col_idx]:
                fig_sp = go.Figure()
                fig_sp.add_trace(go.Scatter(
                    x=sub_bp['일자'], y=sub_bp[c], name=c,
                    line=dict(color=color, width=1.5), showlegend=False,
                    hovertemplate=f'<b>{c}</b>: %{{y:.1f}}bp<br>%{{x|%Y-%m-%d}}<extra></extra>'
                ))
                fig_sp.update_layout(
                    title=dict(text=f'Spread {c} (bp)', font=dict(color='#e6edf3', size=13, family='Noto Sans KR'), x=0),
                    paper_bgcolor='#161b22', plot_bgcolor='#161b22',
                    font=dict(color='#D9DADD', family='Noto Sans KR', size=11),
                    height=260, margin=dict(l=10, r=10, t=36, b=10),
                    hovermode='x unified',
                    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                )
                st.plotly_chart(fig_sp, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 3. IRS — 카드 1x4 왼쪽, 차트 오른쪽
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔄 IRS 금리</div>', unsafe_allow_html=True)

if not irs.empty:
    latest_i = irs.iloc[-1]
    prev_i   = irs.iloc[-2] if len(irs) > 1 else latest_i

    card_col2, chart_col2 = st.columns([1, 2])
    with card_col2:
        for t in ['1Y','3Y','5Y','10Y']:
            chg = (latest_i[t] - prev_i[t]) * 100
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">IRS {t}</div>
                <div class="metric-value">{latest_i[t]:.3f}%</div>
                {delta_html(chg)}
            </div>""", unsafe_allow_html=True)
    with chart_col2:
        fig = make_line_chart(irs, '일자', ['1Y','3Y','5Y','10Y'],
                              'IRS 금리 추이', height=420)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 4. 선물 투자자 동향
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 선물 투자자 순매수 동향</div>', unsafe_allow_html=True)

if not futures.empty:
    col_3y, col_10y = st.columns(2)
    for col_widget, prefix, label in [(col_3y,'3Y','3년'), (col_10y,'10Y','10년')]:
        with col_widget:
            sub = futures.tail(30).copy()
            last_date = sub['일자'].iloc[-1]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sub['일자'], y=sub[f'{prefix}외국인'],
                name='외국인', marker_color='#58a6ff', opacity=0.85))
            fig.add_trace(go.Bar(x=sub['일자'], y=sub[f'{prefix}증권선물'],
                name='증권/선물', marker_color='#3fb950', opacity=0.85))
            fig.add_trace(go.Bar(x=sub['일자'], y=sub[f'{prefix}은행'],
                name='은행', marker_color='#f0883e', opacity=0.85))
            last = sub[sub['일자'] == last_date]
            fig.add_trace(go.Bar(x=last['일자'], y=last[f'{prefix}외국인'],
                name='외국인(당일)', marker_color='#1a6fef', showlegend=True, width=1000*3600*18))
            fig.add_trace(go.Bar(x=last['일자'], y=last[f'{prefix}증권선물'],
                name='증권선물(당일)', marker_color='#1a8f3a', showlegend=True, width=1000*3600*18))
            fig.add_trace(go.Bar(x=last['일자'], y=last[f'{prefix}은행'],
                name='은행(당일)', marker_color='#c05010', showlegend=True, width=1000*3600*18))
            fig.update_layout(**base_layout(f'{label} 국채선물 순매수 (최근 30일)', height=420))
            fig.update_layout(barmode='overlay')
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 5. Bond-Swap Spread 시계열
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔗 Bond-Swap Spread 시계열</div>', unsafe_allow_html=True)

if swap_ts.empty:
    st.warning("⚠️ Swap Time Series 데이터를 불러오지 못했습니다.")

if not swap_ts.empty:
    latest_sw = swap_ts.iloc[-1]
    prev_sw   = swap_ts.iloc[-2] if len(swap_ts) > 1 else latest_sw
    sub_sw    = swap_ts

    # 그룹 정의: (섹션명, [(표시명, 컬럼 prefix)])
    GROUPS = [
        ('공사채',  [('AAA','공사채(AAA)'), ('AA+','공사채(AA+)'), ('AA','공사채(AA0)'), ('AA-','공사채(AA-)')]),
        ('은행채',  [('AAA','은행채(AAA)'), ('AA+','은행채(AA+)'), ('AA','은행채(AA0)'), ('AA-','은행채(AA-)')]),
        ('카드채',  [('AAA','카드채(AAA)'), ('AA+','카드채(AA+)'), ('AA','카드채(AA0)'), ('AA-','카드채(AA-)')]),
        ('회사채',  [('AAA','회사채(AAA)'), ('AA+','회사채(AA+)'), ('AA','회사채(AA)'),  ('AA-','회사채(AA-)')]),
        ('산금채/중금채', [('산금채','산금채'), ('중금채','중금채')]),
    ]
    TENORS_DISP = ['1Y','1.5Y','2Y','3Y']
    TENOR_KEYS  = ['1Y','1.5Y','2Y','3Y']
    COLORS_TENOR = ['#58a6ff','#3fb950','#f0883e','#d2a8ff']
    COLORS_GRADE = ['#58a6ff','#3fb950','#f0883e','#d2a8ff']

    for grp_name, items in GROUPS:
        grp_subheader = f'<div style="color:#8b949e;font-size:14px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin:18px 0 8px 0;padding-left:6px;border-left:2px solid #3d444d;">{grp_name}</div>'
        st.markdown(grp_subheader, unsafe_allow_html=True)

        # 당일값 카드 (만기별 탭 × 등급별 카드)
        tenor_tab = st.tabs(TENORS_DISP)
        for ti, (tenor_disp, tenor_key) in enumerate(zip(TENORS_DISP, TENOR_KEYS)):
            with tenor_tab[ti]:
                metric_c = st.columns(len(items))
                for ci, (grade_name, prefix) in enumerate(items):
                    col_key = f'{prefix}_{tenor_key}'
                    if col_key not in swap_ts.columns:
                        continue
                    val = latest_sw[col_key]
                    chg = latest_sw[col_key] - prev_sw[col_key]
                    with metric_c[ci]:
                        chg_disp = chg * 100 if abs(chg) < 1 else chg
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">{grade_name} ({tenor_disp})</div>
                            <div class="metric-value">{val*100:.2f}bp</div>
                            {delta_html(chg_disp)}
                        </div>""", unsafe_allow_html=True)

        # 추이 차트: 만기별로 1개씩 → 각 차트 안에 등급(AAA/AA+/AA/AA-)을 선으로 표시
        COLORS_GRADE = ['#58a6ff','#3fb950','#f0883e','#d2a8ff','#ffa198']
        chart_cols = st.columns(len(TENORS_DISP))
        for ti2, (tenor_disp, tenor_key) in enumerate(zip(TENORS_DISP, TENOR_KEYS)):
            with chart_cols[ti2]:
                fig_s = go.Figure()
                for ci, (grade_name, prefix) in enumerate(items):
                    col_key = f'{prefix}_{tenor_key}'
                    if col_key not in sub_sw.columns:
                        continue
                    y_bp = sub_sw[col_key] * 100
                    fig_s.add_trace(go.Scatter(
                        x=sub_sw['일자'], y=y_bp,
                        name=grade_name,
                        line=dict(color=COLORS_GRADE[ci % len(COLORS_GRADE)], width=1.5),
                        hovertemplate=f'<b>{grade_name}</b>: %{{y:.2f}}bp<br>%{{x|%Y-%m-%d}}<extra></extra>'
                    ))
                fig_s.update_layout(**base_layout(f'{grp_name} {tenor_disp} (bp)', height=380))
                st.plotly_chart(fig_s, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 6. Bond-Swap Spread 당일 스냅샷 테이블
# ══════════════════════════════════════════════════════════════

if bond_swap_static:
    header = '<tr><th>종목</th>' + ''.join(f'<th>{t}</th>' for t in static_tenors) + '</tr>'
    rows_html = ''
    for rec in bond_swap_static:
        cells = f'<td>{rec["종목"]}</td>'
        for j, v in enumerate(rec['vals']):
            chg = rec['chgs'][j] if rec['chgs'] else None
            v_str = f'{v:.2f}' if pd.notna(v) else '-'
            chg_str = ''
            if chg is not None and pd.notna(chg):
                cls  = 'td-pos' if chg > 0 else 'td-neg' if chg < 0 else ''
                sign = '▲' if chg > 0 else '▼' if chg < 0 else '─'
                chg_str = f'<br><span class="{cls}" style="font-size:13px">{sign}{abs(chg):.2f}</span>'
            cells += f'<td>{v_str}{chg_str}</td>'
        rows_html += f'<tr>{cells}</tr>'
    st.markdown(f'<table class="bond-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div class="refresh-info">🔄 우측 상단 버튼을 눌러 최신 데이터로 갱신하세요</div>',
            unsafe_allow_html=True)
