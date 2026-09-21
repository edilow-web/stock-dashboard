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

# 6. '26년 1~8월(실제) 및 9월 이후(예상) 월별 배당금 현황 표
st.subheader("💰 2026년 월별 배당금 현황 ('26.1~8월: 실제 / '26.9월~: 예상)")

dividend_data = []
# 기준 시점: 2026년 9월 21일 (코드 상 현재 시점)
current_year = 2026
current_month = 9

for idx, row in df.iterrows():
  ticker_str = str(row["Ticker"]).strip()
  qty = row["Quantity"]
  try:
    stock = yf.Ticker(ticker_str)
    dividends = stock.dividends

    if not dividends.empty:
      if dividends.index.tz is not None:
        dividends.index = dividends.index.tz_convert("UTC").tz_localize(None)

      # 2026년 1월 1일 이후의 배당 이력 필터링
      div_2026 = dividends[
          (dividends.index.year == current_year)
          & (dividends.index.month <= 12)
      ]

      # 실제 지급된 내역 (1월 ~ 8월 중 이력이 있는 달)
      actual_divs_by_month = {m: 0.0 for m in range(1, 13)}
      past_months_with_div = []

      for date, val in div_2026.items():
        m = date.month
        if m < current_month:  # 8월 이전
          actual_divs_by_month[m] += val * qty
          if m not in past_months_with_div:
            past_months_with_div.append(m)

      # 향후 예상 지급을 위한 최근 지급 패턴 분석 (최근 1년 데이터 활용)
      recent_year_divs = dividends[
          dividends.index
          >= (pd.Timestamp(f"{current_year}-{current_month}-01") - pd.DateOffset(years=1))
      ]
      monthly_avg_per_share = {m: 0.0 for m in range(1, 13)}
      month_counts = {m: 0 for m in range(1, 13)}

      for date, val in recent_year_divs.items():
        m = date.month
        monthly_avg_per_share[m] += val
        month_counts[m] += 1

      div_row = {
          "종목명": row["Name"],
          "티커": ticker_str,
      }

      total_annual_usd = 0
      has_any_dividend = False

      for m in range(1, 13):
        if m < current_month:
          # '26년 1월 ~ 8월 (실제 확정 금액)
          amt_usd = actual_divs_by_month[m]
          if amt_usd > 0:
            total_annual_usd += amt_usd
            has_any_dividend = True
            amt_krw = amt_usd * exchange_rate
            div_row[f"{m}월"] = (
                f"(실제) $ {amt_usd:,.2f}<br>({amt_krw:,.0f} 원)"
            )
          else:
            div_row[f"{m}월"] = "-"
        else:
          # '26년 9월 ~ 12월 (예상 금액)
          if month_counts[m] > 0:
            amt_usd = monthly_avg_per_share[m] * qty
            total_annual_usd += amt_usd
            has_any_dividend = True
            amt_krw = amt_usd * exchange_rate
            div_row[f"{m}월"] = (
                f"(예상) $ {amt_usd:,.2f}<br>({amt_krw:,.0f} 원)"
            )
          else:
            div_row[f"{m}월"] = "-"

      if has_any_dividend:
        total_annual_krw = total_annual_usd * exchange_rate
        div_row["2026년 총 배당금(합계)"] = (
            f"$ {total_annual_usd:,.2f}<br>({total_annual_krw:,.0f} 원)"
        )
        dividend_data.append(div_row)
  except:
    continue

if len(dividend_data) > 0:
  df_div = pd.DataFrame(dividend_data)

  month_cols = [f"{m}월" for m in range(1, 13)]
  base_cols = ["종목명", "티커"]
  all_cols = base_cols + month_cols + ["2026년 총 배당금(합계)"]

  for col in all_cols:
    if col not in df_div.columns:
      df_div[col] = "-"

  df_div = df_div[all_cols]

  st.markdown(
      df_div.to_html(escape=False, index=False, classes="styled-table"),
      unsafe_allow_html=True,
  )
else:
  st.info("2026년 기준 배당 지급 이력이 있는 종목이 없습니다.")

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
