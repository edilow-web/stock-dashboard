import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="내 투자 대시보드", layout="wide")
st.title("📈 내 투자 포트폴리오 대시보드")

# 1. 포트폴리오 CSV 파일 불러오기
# (구글 시트에서 다운로드한 파일을 같은 폴더에 둔다고 가정)
try:
    df = pd.read_csv("portfolio.csv")
except FileNotFoundError:
    st.error("portfolio.csv 파일이 없습니다. 파일을 업로드해주세요.")
    st.stop()

# 2. yfinance를 이용해 현재가 조회 및 수익률 계산
current_prices = []
for ticker in df['Ticker']:
    try:
        stock = yf.Ticker(str(ticker).strip())
        todays_data = stock.history(period='1d')
        if not todays_data.empty:
            current_prices.append(todays_data['Close'].iloc[-1])
        else:
            current_prices.append(0)
    except:
        current_prices.append(0)

df['Current_Price'] = current_prices
df['Investment'] = df['Buy_Price'] * df['Quantity']
df['Evaluation'] = df['Current_Price'] * df['Quantity']
df['Profit_Loss'] = df['Evaluation'] - df['Investment']
df['Return_Rate'] = (df['Profit_Loss'] / df['Investment']) * 100

# 3. 전체 요약 지표 (상단 카드)
total_investment = df['Investment'].sum()
total_evaluation = df['Evaluation'].sum()
total_profit = total_evaluation - total_investment
total_return = (total_profit / total_investment) * 100 if total_investment > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("총 투자 원금", f"{total_investment:,.0f} 원")
col2.metric("총 평가 금액", f"{total_evaluation:,.0f} 원")
col3.metric("총 수익률", f"{total_return:.2f}%", delta=f"{total_profit:,.0f} 원")

# 4. 종목별 상세 테이블
st.subheader("📊 종목별 보유 현황")
st.dataframe(df[['Name', 'Ticker', 'Buy_Price', 'Current_Price', 'Quantity', 'Return_Rate']], use_container_width=True)

# 5. 종목별 주가 차트
st.subheader("📉 종목별 주가 차트")
selected_ticker = st.selectbox("차트를 볼 종목을 선택하세요", df['Ticker'])
if selected_ticker:
    hist_data = yf.Ticker(str(selected_ticker).strip()).history(period="6mo")
    st.line_chart(hist_data['Close'])