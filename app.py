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
    .metric-delta-neg { color: #3b82f6; font-size: 15px; font-weight: 600; }
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
    .td-neg { color: #3b82f6 !important; }
    .mtd-ytd-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
    .mtd-ytd-table th { background: #1f2937; color: #8b949e; padding: 5px 8px; text-align: center; border: 1px solid #30363d; font-weight: 600; font-size: 11px; letter-spacing: 0.05em; }
    .mtd-ytd-table td { color: #c9d1d9; padding: 5px 8px; text-align: center; border: 1px solid #21262d; font-size: 12px; }
    .mtd-ytd-table td:first-child { color: #8b949e; font-weight: 600; background: #161b22; }
    .mtd-ytd-table .td-pos { color: #f85149 !important; }
    .mtd-ytd-table .td-neg { color: #3b82f6 !important; }
</style>
""", unsafe_allow_html=True)

SHEET_ID    = "1q26oZa4umx6ai1vLloVnCFWNTcsYhelay0AdToyd0Wc"
JSON_PATH   = "stream-dashboard-492904-e1298f3e3f92.json"
GRID_COLOR  = '#3d444d'
MINOR_COLOR = '#2a3038'

# ── 비밀번호 체크 ──────────────────────────────────────────────
def check_password():
    def password_entered():
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
    try:
        import json
        secret_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(secret_dict, scopes=SCOPES)
    except:
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
    """
    cols: 0=일자, 1~7=국고채(1Y~30Y)
          10=sp일자, 11~15=스프레드(2/3~20/30)
          30=5MA날짜, 31~35=5MA(2/3~20/30)
          37~41=20MA(2/3~20/30)
    """
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[0,1,2,3,4,5,6,7,
                     10,11,12,13,14,15,
                     30,31,32,33,34,35,
                     37,38,39,40,41]].copy()
        rows.columns = [
            '일자','1Y','2Y','3Y','5Y','10Y','20Y','30Y',
            'sp일자','2/3','3/10','5/30','10/30','20/30',
            'ma5_일자','5MA_2/3','5MA_3/10','5MA_5/30','5MA_10/30','5MA_20/30',
            '20MA_2/3','20MA_3/10','20MA_5/30','20MA_10/30','20MA_20/30',
        ]
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        rows['ma5_일자'] = pd.to_datetime(rows['ma5_일자'], errors='coerce')
        num_cols = [
            '1Y','2Y','3Y','5Y','10Y','20Y','30Y',
            '2/3','3/10','5/30','10/30','20/30',
            '5MA_2/3','5MA_3/10','5MA_5/30','5MA_10/30','5MA_20/30',
            '20MA_2/3','20MA_3/10','20MA_5/30','20MA_10/30','20MA_20/30',
        ]
        for c in num_cols:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        return rows.dropna(subset=['일자']).sort_values('일자')
    except:
        return pd.DataFrame()

def parse_spread_mtdytd(df):
    """SPREAD 시트 MTD/YTD: row5=MTD, row6=YTD, cols 21~25 (2/3~20/30, bp 단위)"""
    try:
        sp_cols = ['2/3','3/10','5/30','10/30','20/30']
        result = {}
        for label, row_i in [('MTD', 5), ('YTD', 6)]:
            row = df.iloc[row_i, :]
            vals = [pd.to_numeric(row.iloc[j], errors='coerce') for j in range(21, 26)]
            result[label] = dict(zip(sp_cols, vals))
        return result
    except:
        return {}

def parse_irs(df):
    """
    cols: 0=일자, 1=1Y, 2=1.5Y, 3=2Y, 4=3Y
          7=5MA날짜, 8~11=5MA(1Y~3Y)
          14~17=20MA(1Y~3Y)
    """
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[0,1,2,3,4,
                     7,8,9,10,11,
                     14,15,16,17]].copy()
        rows.columns = [
            '일자','1Y','1.5Y','2Y','3Y',
            'ma5_일자','5MA_1Y','5MA_1.5Y','5MA_2Y','5MA_3Y',
            '20MA_1Y','20MA_1.5Y','20MA_2Y','20MA_3Y',
        ]
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        rows['ma5_일자'] = pd.to_datetime(rows['ma5_일자'], errors='coerce')
        num_cols = [
            '1Y','1.5Y','2Y','3Y',
            '5MA_1Y','5MA_1.5Y','5MA_2Y','5MA_3Y',
            '20MA_1Y','20MA_1.5Y','20MA_2Y','20MA_3Y',
        ]
        for c in num_cols:
            rows[c] = pd.to_numeric(rows[c], errors='coerce')
        return rows.dropna(subset=['일자']).sort_values('일자')
    except:
        return pd.DataFrame()

def parse_irs_mtdytd(df):
    """IRS 시트 MTD/YTD: row3=MTD, row4=YTD, cols 22~25 (1Y~3Y, %p 단위)"""
    try:
        irs_cols = ['1Y','1.5Y','2Y','3Y']
        result = {}
        for label, row_i in [('MTD', 3), ('YTD', 4)]:
            row = df.iloc[row_i, :]
            vals = [pd.to_numeric(row.iloc[j], errors='coerce') for j in range(22, 26)]
            result[label] = dict(zip(irs_cols, vals))
        return result
    except:
        return {}

def parse_futures(df):
    try:
        rows = df.iloc[2:].copy()
        rows = rows[[5,6,7,8,9,10,11]].copy()
        rows.columns = ['일자','3Y외국인','3Y증권선물','3Y은행','10Y외국인','10Y증권선물','10Y은행']
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
    """Swap Time Series: tenor가 유효한 컬럼만 선택해 빈 열 오류 방지"""
    try:
        cats_raw   = df.iloc[0, 1:].tolist()
        tenors_raw = df.iloc[1, 1:].tolist()
        cats = []
        cur = None
        for c in cats_raw:
            if c is not None and str(c).strip() not in ['', 'nan', 'None']:
                cur = str(c).strip()
            cats.append(cur)
        valid_indices = []
        valid_col_names = []
        seen = set()
        for i, (c, t) in enumerate(zip(cats, tenors_raw)):
            t_str = str(t).strip() if t is not None and str(t).strip() not in ['', 'nan', 'None'] else ''
            if c and t_str:
                col_key = f'{c}_{t_str}'
                if col_key not in seen:
                    seen.add(col_key)
                    valid_indices.append(i + 1)
                    valid_col_names.append(col_key)
        rows = df.iloc[2:].copy()
        rows = rows.iloc[:, [0] + valid_indices]
        rows.columns = ['일자'] + valid_col_names
        rows['일자'] = pd.to_datetime(rows['일자'], errors='coerce')
        for c in valid_col_names:
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

def mtd_ytd_table_html(data_dict, cols, unit='bp'):
    """MTD/YTD 스냅샷 테이블 HTML"""
    header = '<tr><th></th>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>'
    rows_html = ''
    for label in ['MTD', 'YTD']:
        if label not in data_dict:
            continue
        cells = f'<td>{label}</td>'
        for c in cols:
            v = data_dict[label].get(c, float('nan'))
            try:
                v_f = float(v)
                cls  = 'td-pos' if v_f > 0 else 'td-neg' if v_f < 0 else ''
                sign = '▲' if v_f > 0 else '▼' if v_f < 0 else '─'
                cells += f'<td class="{cls}">{sign}{abs(v_f):.1f}{unit}</td>'
            except:
                cells += '<td>-</td>'
        rows_html += f'<tr>{cells}</tr>'
    return f'<table class="mtd-ytd-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>'

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

spread_raw = data.get('SPREAD', pd.DataFrame())
irs_raw    = data.get('IRS', pd.DataFrame())

spread   = parse_spread(spread_raw)
irs      = parse_irs(irs_raw)
futures  = parse_futures(data.get('KTB Futures', pd.DataFrame()))
swap_ts  = parse_swap_ts(data.get('Swap Time Series', pd.DataFrame()))
static_tenors, bond_swap_static = parse_bond_swap_static(data.get('BOND SWAP', pd.DataFrame()))

spread_mtdytd = parse_spread_mtdytd(spread_raw)
irs_mtdytd    = parse_irs_mtdytd(irs_raw)

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
        fig = go.Figure()
        ktb_colors = ['#58a6ff','#3fb950','#f0883e','#d2a8ff','#ffa198']
        for i, t in enumerate(['3Y','5Y','10Y','20Y','30Y']):
            fig.add_trace(go.Scatter(
                x=spread['일자'], y=spread[t], name=t,
                line=dict(color=ktb_colors[i], width=1.5),
                hovertemplate=f'<b>{t}</b>: %{{y:.3f}}%<br>%{{x|%Y-%m-%d}}<extra></extra>'
            ))
        fig.update_layout(**base_layout('국고채 금리 추이'))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # ── 수익률 곡선: 날짜 3개 선택 비교 ──
        st.markdown('<div style="color:#8b949e;font-size:12px;font-weight:600;margin-bottom:6px;letter-spacing:0.04em;">📅 비교 날짜 선택 (최대 3개)</div>', unsafe_allow_html=True)
        available_dates = spread['일자'].dt.date.tolist()[::-1]

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            d1 = st.selectbox('날짜1', available_dates, index=0, key='yc_d1',
                              label_visibility='collapsed')
        with col_d2:
            default_1m = min(range(len(available_dates)),
                key=lambda i: abs((pd.Timestamp(available_dates[i]) -
                    (pd.Timestamp(available_dates[0]) - pd.DateOffset(months=1))).days))
            d2 = st.selectbox('날짜2', available_dates, index=default_1m, key='yc_d2',
                              label_visibility='collapsed')
        with col_d3:
            default_1y = min(range(len(available_dates)),
                key=lambda i: abs((pd.Timestamp(available_dates[i]) -
                    (pd.Timestamp(available_dates[0]) - pd.DateOffset(years=1))).days))
            d3 = st.selectbox('날짜3', available_dates, index=default_1y, key='yc_d3',
                              label_visibility='collapsed')

        yc_colors = ['#58a6ff','#3fb950','#f0883e']
        yc_dashes = ['solid','dash','dot']
        yc_widths = [2, 1.5, 1.5]
        x_axis    = ['2Y','3Y','5Y','10Y','20Y','30Y']
        fig2 = go.Figure()
        for di, sel_date in enumerate([d1, d2, d3]):
            sel_ts = pd.Timestamp(sel_date)
            idx    = (spread['일자'] - sel_ts).abs().idxmin()
            row    = spread.loc[idx]
            fig2.add_trace(go.Scatter(
                x=x_axis, y=[row[t] for t in x_axis],
                mode='lines+markers',
                line=dict(color=yc_colors[di], width=yc_widths[di], dash=yc_dashes[di]),
                marker=dict(size=6 if di == 0 else 5),
                name=row['일자'].strftime('%y.%m.%d')
            ))
        fig2.update_layout(**base_layout('수익률 곡선 비교', height=420))
        fig2.update_layout(xaxis=grid_axis())
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 2. 스프레드 분석
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📐 스프레드 분석</div>', unsafe_allow_html=True)

if not spread.empty:
    latest_s = spread.iloc[-1]
    prev_s   = spread.iloc[-2] if len(spread) > 1 else latest_s
    sp_cols   = ['2/3','3/10','5/30','10/30','20/30']
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

        # MTD / YTD 테이블
        if spread_mtdytd:
            st.markdown('<div style="margin-top:14px;color:#8b949e;font-size:11px;font-weight:600;letter-spacing:0.06em;">MTD / YTD (bp)</div>', unsafe_allow_html=True)
            st.markdown(mtd_ytd_table_html(spread_mtdytd, sp_cols, unit='bp'),
                        unsafe_allow_html=True)

    with chart_col:
        # 5개 개별 차트 — 각각 독립 zoom, 5MA·20MA 포함
        sub_bp = spread.copy()
        for c in sp_cols:
            sub_bp[c]           = sub_bp[c]           * 100
            sub_bp[f'5MA_{c}']  = sub_bp[f'5MA_{c}']  * 100
            sub_bp[f'20MA_{c}'] = sub_bp[f'20MA_{c}'] * 100

        chart_grid_rows = [st.columns(2), st.columns(2), st.columns(2)]
        positions_grid  = [(0,0),(0,1),(1,0),(1,1),(2,0)]
        for i, (c, color, pos) in enumerate(zip(sp_cols, sp_colors, positions_grid)):
            row_idx, col_idx = pos
            with chart_grid_rows[row_idx][col_idx]:
                fig_sp = go.Figure()
                fig_sp.add_trace(go.Scatter(
                    x=sub_bp['일자'], y=sub_bp[c], name=c,
                    line=dict(color=color, width=1.5), showlegend=True,
                    hovertemplate=f'<b>{c}</b>: %{{y:.1f}}bp<br>%{{x|%Y-%m-%d}}<extra></extra>'
                ))
                if f'5MA_{c}' in sub_bp.columns:
                    fig_sp.add_trace(go.Scatter(
                        x=sub_bp['일자'], y=sub_bp[f'5MA_{c}'], name='5MA',
                        line=dict(color='#ffa198', width=0.9), showlegend=True,
                        hovertemplate='<b>5MA</b>: %{y:.1f}bp<extra></extra>'
                    ))
                if f'20MA_{c}' in sub_bp.columns:
                    fig_sp.add_trace(go.Scatter(
                        x=sub_bp['일자'], y=sub_bp[f'20MA_{c}'], name='20MA',
                        line=dict(color='#d2a8ff', width=0.9), showlegend=True,
                        hovertemplate='<b>20MA</b>: %{y:.1f}bp<extra></extra>'
                    ))
                fig_sp.update_layout(
                    title=dict(text=f'Spread {c} (bp)', font=dict(color='#e6edf3', size=13, family='Noto Sans KR'), x=0),
                    paper_bgcolor='#161b22', plot_bgcolor='#161b22',
                    font=dict(color='#D9DADD', family='Noto Sans KR', size=11),
                    height=290, margin=dict(l=10, r=10, t=36, b=10),
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='left', x=0,
                                font=dict(size=10, color='#D9DADD'), bgcolor='rgba(0,0,0,0)'),
                    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                )
                st.plotly_chart(fig_sp, use_container_width=True)

# ══════════════════════════════════════════════════════════════
# 3. IRS 금리 — 1Y·1.5Y·2Y·3Y, 4개 개별 차트 + 5MA/20MA
# ══════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🔄 IRS 금리</div>', unsafe_allow_html=True)

if not irs.empty:
    latest_i   = irs.iloc[-1]
    prev_i     = irs.iloc[-2] if len(irs) > 1 else latest_i
    irs_tenors = ['1Y','1.5Y','2Y','3Y']
    irs_colors = ['#58a6ff','#3fb950','#f0883e','#d2a8ff']

    card_col2, chart_col2 = st.columns([1, 3])
    with card_col2:
        for t in irs_tenors:
            chg = (latest_i[t] - prev_i[t]) * 100
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">IRS {t}</div>
                <div class="metric-value">{latest_i[t]:.3f}%</div>
                {delta_html(chg)}
            </div>""", unsafe_allow_html=True)

        # MTD / YTD 테이블
        if irs_mtdytd:
            st.markdown('<div style="margin-top:14px;color:#8b949e;font-size:11px;font-weight:600;letter-spacing:0.06em;">MTD / YTD (bp)</div>', unsafe_allow_html=True)
            st.markdown(mtd_ytd_table_html(irs_mtdytd, irs_tenors, unit='bp'),
                        unsafe_allow_html=True)

    with chart_col2:
        # 4개 개별 차트 (2×2) — 각각 독립 zoom, 5MA·20MA 포함
        irs_chart_rows = [st.columns(2), st.columns(2)]
        irs_positions  = [(0,0),(0,1),(1,0),(1,1)]
        for i, (t, color, pos) in enumerate(zip(irs_tenors, irs_colors, irs_positions)):
            row_idx, col_idx = pos
            with irs_chart_rows[row_idx][col_idx]:
                fig_irs = go.Figure()
                fig_irs.add_trace(go.Scatter(
                    x=irs['일자'], y=irs[t], name=f'IRS {t}',
                    line=dict(color=color, width=1.5), showlegend=True,
                    hovertemplate=f'<b>IRS {t}</b>: %{{y:.3f}}%<br>%{{x|%Y-%m-%d}}<extra></extra>'
                ))
                ma5_col  = f'5MA_{t}'
                ma20_col = f'20MA_{t}'
                if ma5_col in irs.columns:
                    fig_irs.add_trace(go.Scatter(
                        x=irs['일자'], y=irs[ma5_col], name='5MA',
                        line=dict(color='#ffa198', width=0.9), showlegend=True,
                        hovertemplate='<b>5MA</b>: %{y:.3f}%<extra></extra>'
                    ))
                if ma20_col in irs.columns:
                    fig_irs.add_trace(go.Scatter(
                        x=irs['일자'], y=irs[ma20_col], name='20MA',
                        line=dict(color='#d2a8ff', width=0.9), showlegend=True,
                        hovertemplate='<b>20MA</b>: %{y:.3f}%<extra></extra>'
                    ))
                fig_irs.update_layout(
                    title=dict(text=f'IRS {t}', font=dict(color='#e6edf3', size=13, family='Noto Sans KR'), x=0),
                    paper_bgcolor='#161b22', plot_bgcolor='#161b22',
                    font=dict(color='#D9DADD', family='Noto Sans KR', size=11),
                    height=310, margin=dict(l=10, r=10, t=36, b=10),
                    hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='left', x=0,
                                font=dict(size=10, color='#D9DADD'), bgcolor='rgba(0,0,0,0)'),
                    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
                               minor=dict(showgrid=True, gridcolor=MINOR_COLOR),
                               tickfont=dict(color='#D9DADD', size=10)),
                )
                st.plotly_chart(fig_irs, use_container_width=True)

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

    GROUPS = [
        ('공사채',       [('AAA','공사채(AAA)'), ('AA+','공사채(AA+)'), ('AA','공사채(AA0)'), ('AA-','공사채(AA-)')]),
        ('은행채',       [('AAA','은행채(AAA)'), ('AA+','은행채(AA+)'), ('AA','은행채(AA0)'), ('AA-','은행채(AA-)')]),
        ('카드채',       [('AA+','카드채(AA+)'), ('AA','카드채(AA0)'), ('AA-','카드채(AA-)')]),
        ('회사채',       [('AAA','회사채(AAA)'), ('AA+','회사채(AA+)'), ('AA','회사채(AA)'),  ('AA-','회사채(AA-)')]),
        ('산금채/중금채', [('산금채','산금채'), ('중금채','중금채')]),
    ]
    TENORS_DISP  = ['1Y','1.5Y','2Y','3Y']
    TENOR_KEYS   = ['1Y','1.5Y','2Y','3Y']
    COLORS_GRADE = ['#58a6ff','#3fb950','#f0883e','#d2a8ff','#ffa198']

    for grp_name, items in GROUPS:
        grp_subheader = f'<div style="color:#8b949e;font-size:14px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;margin:18px 0 8px 0;padding-left:6px;border-left:2px solid #3d444d;">{grp_name}</div>'
        st.markdown(grp_subheader, unsafe_allow_html=True)

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
