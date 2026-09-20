from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="내 투자 대시보드", layout="wide")
st.title("📈 내 투자 포트폴리오 대시보드")


# 1. 실시간 원/달러 환율 및 기준 시간 가져오기 함수
@st.cache_data(ttl=3600)
def get_exchange_rate_and_time():
  try:
    exc = yf.Ticker("USDKRW=X")
    hist = exc.history(period="1d")
    rate = hist["Close"].iloc[-1]
    # 데이터의 마지막 갱신 시간 가져오기 (한국 시간대 또는 거래소 기준)
    last_time = hist.index[-1].strftime("%Y년 %m월 %d일 %H시 %M분")
    return rate, last_time
  except:
    now_str = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    return 1350.0, now_str


exchange_rate, rate_time = get_exchange_rate_and_time()

# 💡 화면 최상단에 환율 정보와 정확한 기준 일시를 함께 표시
st.metric(
    label=f"💱 실시간 기준 원/달러 환율 (기준 시점: {rate_time})",
    value=f"{exchange_rate:,.2f} 원",
)
st.divider()

# 2. 포트폴리오 CSV 파일 불러오기
try:
  df = pd.read_csv("portfolio.csv")
except FileNotFoundError:
  st.error("portfolio.csv 파일이 없습니다. 파일을 업로드해주세요.")
  st.stop()

# 'Buy_Price'에 혹시 '달러'나 특수문자가 섞여 있어도 숫자로 깔끔하게 변환
if "Buy_Price" in df.columns:
  df["Buy_Price"] = (
      df["Buy_Price"]
      .astype(str)
      .str.replace(r"[^0-9.]", "", regex=True)
      .astype(float)
  )

# 3. yfinance를 이용해 현재가 조회 및 수익률 계산
current_prices = []
for ticker in df["Ticker"]:
  try:
    stock = yf.Ticker(str(ticker).strip())
    todays_data = stock.history(period="1d")
    if not todays_data.empty:
      current_prices.append(todays_data["Close"].iloc[-1])
    else:
      current_prices.append(0)
  except:
    current_prices.append(0)

df["Current_Price"] = current_prices
df["Investment"] = df["Buy_Price"] * df["Quantity"]
df["Evaluation"] = df["Current_Price"] * df["Quantity"]
df["Profit_Loss"] = df["Evaluation"] - df["Investment"]
df["Return_Rate"] = (df["Profit_Loss"] / df["Investment"]) * 100

# 4. 전체 요약 지표 (상단 카드 - 달러 및 원화 병행 표시)
total_investment = df["Investment"].sum()
total_evaluation = df["Evaluation"].sum()
total_profit = total_evaluation - total_investment
total_return = (
    (total_profit / total_investment) * 100 if total_investment > 0 else 0
)

# 원화 환산 금액 계산
total_investment_krw = total_investment * exchange_rate
total_evaluation_krw = total_evaluation * exchange_rate
total_profit_krw = total_profit * exchange_rate

col1, col2, col3 = st.columns(3)
col1.metric(
    "총 투자 원금",
    f"${total_investment:,.2f}",
    f"{total_investment_krw:,.0f} 원",
)
col2.metric(
    "총 평가 금액",
    f"${total_evaluation:,.2f}",
    f"{total_evaluation_krw:,.0f} 원",
)
col3.metric(
    "총 수익률",
    f"${total_return:.2f}%",
    delta=(
        f"${total_profit:,.2f} ({total_profit_krw:+,.0f} 원)"
        if total_profit != 0
        else "$0.00"
    ),
)

st.divider()

# 5. 종목별 상세 테이블 (원화 환산 가격 추가)
st.subheader("📊 종목별 보유 현황")

# 원화 환산 컬럼 추가
df["Buy_Price_KRW"] = df["Buy_Price"] * exchange_rate
df["Current_Price_KRW"] = df["Current_Price"] * exchange_rate

df_display = df[
    [
        "Name",
        "Ticker",
        "Buy_Price",
        "Buy_Price_KRW",
        "Current_Price",
        "Current_Price_KRW",
        "Quantity",
        "Return_Rate",
    ]
].copy()
df_display.columns = [
    "종목명",
    "티커",
    "매수가 ($)",
    "매수가 (원)",
    "현재가 ($)",
    "현재가 (원)",
    "보유수량",
    "수익률 (%)",
]

# 포맷팅 적용
df_display["매수가 ($)"] = df_display["매수가 ($)"].map("${:,.2f}".format)
df_display["매수가 (원)"] = df_display["매수가 (원)"].map(
    "{:,.0f} 원".format
)
df_display["현재가 ($)"] = df_display["현재가 ($)"].map("${:,.2f}".format)
df_display["현재가 (원)"] = df_display["현재가 (원)"].map(
    "{:,.0f} 원".format
)
df_display["수익률 (%)"] = df_display["수익률 (%)"].map("{:+.2f}%".format)

st.dataframe(df_display, use_container_width=True)

st.divider()

# 6. 종목별 주가 차트
st.subheader("📉 종목별 주가 차트")
selected_ticker = st.selectbox(
    "차트를 볼 종목을 선택하세요", df["Ticker"].tolist()
)
if selected_ticker:
  hist_data = yf.Ticker(str(selected_ticker).strip()).history(period="6mo")
  if not hist_data.empty:
    fig = px.line(
        hist_data,
        x=hist_data.index,
        y="Close",
        title=f"{selected_ticker} 최근 6개월 주가 추이",
        labels={"Close": "가격 ($)", "Date": "날짜"},
    )
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.warning("차트 데이터를 불러올 수 없습니다.")
