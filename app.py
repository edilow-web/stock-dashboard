from datetime import datetime, timedelta
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
    last_time = hist.index[-1].strftime("%Y년 %m월 %d일 %H시 %M분")
    return rate, last_time
  except:
    now_str = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    return 1350.0, now_str


exchange_rate, rate_time = get_exchange_rate_and_time()

# 💡 화면 최상단에 환율 정보와 기준 일시 표시
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

# 3. yfinance를 이용해 현재가 조회 및 계산
current_prices = []
for ticker in df["Ticker"]:
  try:
    stock = yf.Ticker(str(ticker).strip())
    todays_data = stock.history(period="1d")
    if not todays_data.empty:
      current_prices.append(todays_data["Close"].iloc[-1])
    else:
      current_prices.append(0.0)
  except:
    current_prices.append(0.0)

df["Current_Price"] = current_prices
df["Investment"] = df["Buy_Price"] * df["Quantity"]
df["Evaluation"] = df["Current_Price"] * df["Quantity"]
df["Profit_Loss"] = df["Evaluation"] - df["Investment"]
df["Return_Rate"] = (df["Profit_Loss"] / df["Investment"]) * 100

# 4. 전체 요약 지표 (상단 카드)
total_investment = df["Investment"].sum()
total_evaluation = df["Evaluation"].sum()
total_profit = total_evaluation - total_investment
total_return = (
    (total_profit / total_investment) * 100 if total_investment > 0 else 0
)

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

# 5. 종목별 상세 테이블 구성 (달러 아래에 원화 세로 병기)
st.subheader("📊 종목별 보유 현황")

display_data = []
for idx, row in df.iterrows():
  buy_usd = row["Buy_Price"]
  buy_krw = buy_usd * exchange_rate
  buy_str = f"$ {buy_usd:,.2f}<br>({buy_krw:,.0f} 원)"

  cur_usd = row["Current_Price"]
  cur_krw = cur_usd * exchange_rate
  cur_str = f"$ {cur_usd:,.2f}<br>({cur_krw:,.0f} 원)"

  eval_usd = row["Evaluation"]
  eval_krw = eval_usd * exchange_rate
  eval_str = f"$ {eval_usd:,.2f}<br>({eval_krw:,.0f} 원)"

  ret_str = f"{row['Return_Rate']:+.2f}%"

  display_data.append({
      "종목명": row["Name"],
      "티커": row["Ticker"],
      "매수가": buy_str,
      "현재가": cur_str,
      "보유수량": row["Quantity"],
      "총 평가금액": eval_str,
      "수익률": ret_str,
  })

df_display = pd.DataFrame(display_data)

st.markdown(
    df_display.to_html(escape=False, index=False, classes="styled-table"),
    unsafe_allow_html=True,
)

st.divider()

# 6. 현재 시점 기준 향후 1년간 월별 예상 배당금 현황 표
st.subheader(
    "💰 향후 1년 월별 예상 배당금 현황 (현재 기준 향후 12개월, 배당 지급 종목"
    " 대상)"
)

dividend_data = []
now = pd.Timestamp.now(tz="UTC")  # 현재 시점 기준
one_year_later = now + pd.DateOffset(years=1)

for idx, row in df.iterrows():
  ticker_str = str(row["Ticker"]).strip()
  qty = row["Quantity"]
  try:
    stock = yf.Ticker(ticker_str)
    dividends = stock.dividends

    if not dividends.empty:
      # 타임존 일치시키기
      if dividends.index.tz is not None and now.tz is not None:
        dividends.index = dividends.index.tz_convert("UTC")
      elif dividends.index.tz is None and now.tz is not None:
        dividends.index = dividends.index.tz_localize("UTC")

      # 직전 1년(최근 12개월) 데이터를 분석하여 배당 주기 및 주당 지급액 파악
      past_year_divs = dividends[dividends.index >= (now - pd.DateOffset(years=1))]

      if not past_year_divs.empty:
        # 월별 평균 배당금 계산
        monthly_avg_per_share = {i: 0.0 for i in range(1, 13)}
        month_counts = {i: 0 for i in range(1, 13)}

        for date, val in past_year_divs.items():
          m = date.month
          monthly_avg_per_share[m] += val
          month_counts[m] += 1

        div_row = {
            "종목명": row["Name"],
            "티커": ticker_str,
        }
        annual_total_usd = 0
        has_dividend = False

        for m in range(1, 13):
          if month_counts[m] > 0:
            amt_usd = monthly_avg_per_share[m] * qty
            annual_total_usd += amt_usd
            has_dividend = True
            amt_krw = amt_usd * exchange_rate
            div_row[f"{m}월"] = (
                f"(예상) $ {amt_usd:,.2f}<br>({amt_krw:,.0f} 원)"
            )
          else:
            div_row[f"{m}월"] = "-"

        if has_dividend:
          annual_total_krw = annual_total_usd * exchange_rate
          div_row["향후 1년 예상 총 배당금"] = (
              f"(예상) $ {annual_total_usd:,.2f}<br>({annual_total_krw:,.0f}"
              " 원)"
          )
          dividend_data.append(div_row)
  except:
    continue

if len(dividend_data) > 0:
  df_div = pd.DataFrame(dividend_data)

  # 현재 월부터 시작하거나 1~12월 순서로 정렬 (일반적인 1~12월 달력 순서 유지)
  month_cols = [f"{m}월" for m in range(1, 13)]
  base_cols = ["종목명", "티커"]
  all_cols = base_cols + month_cols + ["향후 1년 예상 총 배당금"]

  for col in all_cols:
    if col not in df_div.columns:
      df_div[col] = "-"

  df_div = df_div[all_cols]

  st.markdown(
      df_div.to_html(escape=False, index=False, classes="styled-table"),
      unsafe_allow_html=True,
  )
else:
  st.info("현재 포트폴리오에 향후 배당이 예상되는 종목이 없습니다.")

st.divider()

# 7. 종목별 주가 차트
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
