import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from derivative_analyzer import DerivativeAnalyzer, calculate_implied_volatility

# Page configuration
st.set_page_config(
    page_title="Derivative Trading Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .positive {
        color: #00cc96;
    }
    .negative {
        color: #ef553b;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header">📊 Derivative Trading Analyzer</div>', unsafe_allow_html=True)
    
    # Initialize analyzer in session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = DerivativeAnalyzer()
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox("Choose Analysis Mode", 
                                   ["Portfolio Manager", "Option Pricing", "Risk Analysis", "Scenario Analysis"])
    
    # Risk-free rate input
    st.sidebar.subheader("Settings")
    risk_free_rate = st.sidebar.number_input("Risk-Free Rate (%)", value=5.0, min_value=0.0, max_value=20.0, step=0.1) / 100
    st.session_state.analyzer.risk_free_rate = risk_free_rate
    
    if app_mode == "Portfolio Manager":
        show_portfolio_manager()
    elif app_mode == "Option Pricing":
        show_option_pricing()
    elif app_mode == "Risk Analysis":
        show_risk_analysis()
    elif app_mode == "Scenario Analysis":
        show_scenario_analysis()

def show_portfolio_manager():
    st.header("📋 Portfolio Manager")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Add New Position")
        
        position_type = st.selectbox("Position Type", ["Option", "Future"])
        symbol = st.text_input("Symbol", "AAPL")
        quantity = st.number_input("Quantity", value=1, min_value=1)
        underlying_price = st.number_input("Underlying Price", value=100.0, min_value=0.0, step=0.1)
        
        if position_type == "Option":
            option_type = st.selectbox("Option Type", ["Call", "Put"])
            strike = st.number_input("Strike Price", value=105.0, min_value=0.0, step=0.1)
            expiration = st.date_input("Expiration Date", datetime.now() + timedelta(days=30))
            volatility = st.number_input("Volatility (%)", value=20.0, min_value=0.1, max_value=500.0, step=0.1) / 100
            entry_price = st.number_input("Entry Price (optional)", value=0.0, min_value=0.0, step=0.1)
            
            if st.button("Add Option Position"):
                try:
                    st.session_state.analyzer.add_position(
                        symbol=f"{symbol}_{option_type.upper()}_{strike}",
                        underlying_price=underlying_price,
                        strike=strike,
                        expiration=expiration,
                        volatility=volatility,
                        option_type=option_type.lower(),
                        quantity=quantity,
                        entry_price=entry_price if entry_price > 0 else None
                    )
                    st.success(f"Added {option_type} option position for {symbol}")
                except Exception as e:
                    st.error(f"Error adding position: {e}")
        
        else:  # Future
            entry_price_future = st.number_input("Entry Price", value=underlying_price, min_value=0.0, step=0.1)
            
            if st.button("Add Future Position"):
                st.session_state.analyzer.add_position(
                    symbol=f"{symbol}_FUTURE",
                    underlying_price=underlying_price,
                    strike=0,  # Not used for futures
                    expiration=datetime.now(),
                    volatility=0,
                    position_type='future',
                    quantity=quantity,
                    entry_price=entry_price_future
                )
                st.success(f"Added future position for {symbol}")
    
    with col2:
        st.subheader("Current Portfolio")
        
        if not st.session_state.analyzer.portfolio:
            st.info("No positions in portfolio. Add positions using the form on the left.")
        else:
            # Display portfolio summary
            portfolio_df = st.session_state.analyzer.get_portfolio_summary()
            st.dataframe(portfolio_df, use_container_width=True)
            
            # Portfolio statistics
            st.subheader("Portfolio Overview")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_value = sum(pos['current_price'] * abs(pos['quantity']) 
                                for pos in st.session_state.analyzer.portfolio.values())
                st.metric("Total Portfolio Value", f"${total_value:,.2f}")
            
            with col2:
                st.metric("Number of Positions", len(st.session_state.analyzer.portfolio))
            
            with col3:
                option_count = sum(1 for pos in st.session_state.analyzer.portfolio.values() 
                                 if pos['type'] == 'option')
                st.metric("Option Positions", option_count)
            
            # Clear portfolio button
            if st.button("Clear All Positions"):
                st.session_state.analyzer.portfolio = {}
                st.rerun()

def show_option_pricing():
    st.header("💰 Option Pricing Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pricing Inputs")
        underlying_price = st.number_input("Underlying Price", value=100.0, min_value=0.0, step=0.1, key="pricing_underlying")
        strike_price = st.number_input("Strike Price", value=105.0, min_value=0.0, step=0.1, key="pricing_strike")
        days_to_expiry = st.number_input("Days to Expiration", value=30, min_value=0, max_value=3650, key="pricing_days")
        volatility = st.number_input("Volatility (%)", value=20.0, min_value=0.1, max_value=500.0, step=0.1, key="pricing_vol") / 100
        option_type = st.selectbox("Option Type", ["Call", "Put"], key="pricing_type")
        
        if st.button("Calculate Option Price"):
            time_to_expiry = days_to_expiry / 365.0
            greeks = st.session_state.analyzer.black_scholes(
                underlying_price, strike_price, time_to_expiry, volatility, option_type.lower()
            )
            
            st.session_state.pricing_result = greeks
    
    with col2:
        st.subheader("Implied Volatility Calculator")
        market_price = st.number_input("Market Price", value=2.5, min_value=0.0, step=0.1, key="iv_market_price")
        
        if st.button("Calculate Implied Volatility"):
            time_to_expiry = days_to_expiry / 365.0
            iv = calculate_implied_volatility(
                underlying_price, strike_price, time_to_expiry, market_price, 
                option_type.lower(), st.session_state.analyzer.risk_free_rate
            )
            
            st.metric("Implied Volatility", f"{iv*100:.2f}%")
    
    # Display results
    if 'pricing_result' in st.session_state:
        greeks = st.session_state.pricing_result
        
        st.subheader("Pricing Results")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Option Price", f"${greeks['price']:.2f}")
        with col2:
            delta_color = "positive" if greeks['delta'] > 0 else "negative"
            st.metric("Delta", f"{greeks['delta']:.4f}", delta=greeks['delta'])
        with col3:
            st.metric("Gamma", f"{greeks['gamma']:.4f}")
        with col4:
            st.metric("Theta", f"{greeks['theta']:.4f}")
        with col5:
            st.metric("Vega", f"{greeks['vega']:.4f}")
        with col6:
            st.metric("Rho", f"{greeks['rho']:.4f}")
        
        # Profit/Loss diagram
        st.subheader("Profit/Loss Diagram")
        spot_prices = np.linspace(underlying_price * 0.7, underlying_price * 1.3, 100)
        pnl_values = []
        
        for spot in spot_prices:
            greeks_spot = st.session_state.analyzer.black_scholes(
                spot, strike_price, time_to_expiry, volatility, option_type.lower()
            )
            pnl = (greeks_spot['price'] - greeks['price']) * 100  # Assuming 1 contract = 100 shares
            pnl_values.append(pnl)
        
        fig = px.line(x=spot_prices, y=pnl_values, 
                     labels={'x': 'Underlying Price', 'y': 'P&L ($)'},
                     title=f"{option_type} Option P&L Profile")
        fig.add_vline(x=strike_price, line_dash="dash", line_color="red", annotation_text="Strike")
        fig.add_hline(y=0, line_dash="solid", line_color="black")
        st.plotly_chart(fig, use_container_width=True)

def show_risk_analysis():
    st.header("⚠️ Risk Analysis")
    
    if not st.session_state.analyzer.portfolio:
        st.warning("No positions in portfolio. Add positions in the Portfolio Manager.")
        return
    
    # Portfolio Greeks
    st.subheader("Portfolio Greeks")
    portfolio_greeks = st.session_state.analyzer.calculate_portfolio_greeks()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        delta_color = "positive" if portfolio_greeks['delta'] > 0 else "negative"
        st.metric("Delta", f"{portfolio_greeks['delta']:.4f}")
    with col2:
        st.metric("Gamma", f"{portfolio_greeks['gamma']:.4f}")
    with col3:
        st.metric("Theta", f"{portfolio_greeks['theta']:.4f}")
    with col4:
        st.metric("Vega", f"{portfolio_greeks['vega']:.4f}")
    with col5:
        st.metric("Rho", f"{portfolio_greeks['rho']:.4f}")
    
    # Risk Metrics
    st.subheader("Risk Metrics")
    risk_metrics = st.session_state.analyzer.risk_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Portfolio Value", f"${risk_metrics['portfolio_value']:,.2f}")
    with col2:
        st.metric("1-Day VaR (95%)", f"${risk_metrics['var_95']:,.2f}")
    with col3:
        st.metric("Position Count", risk_metrics['position_count'])
    with col4:
        st.metric("Diversification Score", f"{risk_metrics['diversification_score']:.1%}")
    
    # Greek Sensitivity Analysis
    st.subheader("Greek Sensitivity Analysis")
    
    option_positions = [pos for pos in st.session_state.analyzer.portfolio.values() 
                       if pos['type'] == 'option']
    
    if option_positions:
        greek_type = st.selectbox("Select Greek", ["delta", "gamma", "theta", "vega"])
        prices, greeks = st.session_state.analyzer.generate_greek_sensitivity_data(greek_type)
        
        if prices is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=prices, y=greeks, mode='lines', name=greek_type.capitalize()))
            fig.add_vline(x=option_positions[0]['underlying_price'], line_dash="dash", 
                         line_color="red", annotation_text="Current Price")
            fig.update_layout(title=f"{greek_type.capitalize()} Sensitivity",
                             xaxis_title="Underlying Price",
                             yaxis_title=f"{greek_type.capitalize()} Value")
            st.plotly_chart(fig, use_container_width=True)

def show_scenario_analysis():
    st.header("🔮 Scenario Analysis")
    
    if not st.session_state.analyzer.portfolio:
        st.warning("No positions in portfolio. Add positions in the Portfolio Manager.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        price_change = st.slider("Price Change (%)", -20.0, 20.0, 0.0, 1.0)
    with col2:
        vol_change = st.slider("Volatility Change (absolute)", -0.2, 0.2, 0.0, 0.01)
    with col3:
        days_passed = st.slider("Days Passed", 0, 30, 0, 1)
    
    if st.button("Run Scenario Analysis"):
        pnl_results = st.session_state.analyzer.profit_loss_analysis(
            price_change/100, vol_change, days_passed
        )
        
        st.subheader("Scenario Results")
        
        # Total P&L
        total_pnl = pnl_results['total_pnl']
        pnl_color = "positive" if total_pnl >= 0 else "negative"
        
        st.metric("Total Portfolio P&L", f"${total_pnl:,.2f}", 
                 delta=f"{total_pnl:,.2f}")
        
        # Individual position P&L
        st.subheader("Position-wise P&L")
        pnl_data = []
        for symbol, result in pnl_results.items():
            if symbol != 'total_pnl':
                pnl_data.append({
                    'Symbol': symbol,
                    'P&L ($)': result['pnl'],
                    'P&L (%)': result['pnl_percent']
                })
        
        pnl_df = pd.DataFrame(pnl_data)
        st.dataframe(pnl_df, use_container_width=True)
        
        # Scenario comparison
        st.subheader("Multiple Scenario Comparison")
        scenarios = [
            ("Base Case", 0, 0, 0),
            ("Market Up 10%", 10, 0, 0),
            ("Market Down 10%", -10, 0, 0),
            ("Volatility Spike", 0, 0.1, 0),
            ("1 Week Decay", 0, 0, 7)
        ]
        
        scenario_results = []
        for name, price_chg, vol_chg, days in scenarios:
            pnl = st.session_state.analyzer.profit_loss_analysis(
                price_chg/100, vol_chg, days
            )['total_pnl']
            scenario_results.append({'Scenario': name, 'P&L': pnl})
        
        scenario_df = pd.DataFrame(scenario_results)
        
        fig = px.bar(scenario_df, x='Scenario', y='P&L', 
                    title="P&L Across Different Scenarios",
                    color='P&L', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
