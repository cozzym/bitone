import streamlit as st
import yfinance as yf
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class LoanState:
    btc_collateral: float
    price: float
    ltv_ratio: float
    loan_amount: float
    initial_cash: float
    remaining_cash: float

    @property
    def collateral_value(self) -> float:
        return self.btc_collateral * self.price

class BitcoinLoanCalculator:
    @staticmethod
    def get_live_price() -> Optional[float]:
        """Fetches current Bitcoin price in EUR."""
        try:
            ticker = yf.Ticker("BTC-EUR")
            data = ticker.history(period="1d")
            return float(data['Close'].iloc[-1]) if not data.empty else None
        except Exception as e:
            st.error(f"Error fetching Bitcoin price: {e}")
            return None

    @staticmethod
    def calculate_rebalance(
        state: LoanState,
        new_price: float,
        ltv_trigger: float
    ) -> Dict:
        """
        Calculate rebalancing needs based on new price and available cash.
        Returns dict with rebalancing details.
        """
        new_collateral_value = state.btc_collateral * new_price
        current_ltv = (state.loan_amount / new_collateral_value) * 100

        if current_ltv < ltv_trigger:
            return {
                "needs_rebalance": False,
                "current_ltv": current_ltv,
                "btc_to_buy": 0,
                "cash_needed": 0,
                "can_fully_rebalance": True,
                "new_btc_total": state.btc_collateral,
                "new_ltv": current_ltv,
                "cash_used": 0,
                "cash_remaining": state.remaining_cash,
                "total_cash_required": 0
            }

        target_collateral_value = state.loan_amount / (state.ltv_ratio / 100)
        additional_collateral_needed = target_collateral_value - new_collateral_value
        total_btc_needed = additional_collateral_needed / new_price
        total_cash_required = total_btc_needed * new_price

        can_fully_rebalance = total_cash_required <= state.remaining_cash
        
        if not can_fully_rebalance:
            actual_btc_to_buy = state.remaining_cash / new_price
            cash_used = state.remaining_cash
            new_btc_total = state.btc_collateral + actual_btc_to_buy
        else:
            actual_btc_to_buy = total_btc_needed
            cash_used = total_cash_required
            new_btc_total = state.btc_collateral + total_btc_needed

        new_collateral_value = new_btc_total * new_price
        new_ltv = (state.loan_amount / new_collateral_value) * 100

        return {
            "needs_rebalance": True,
            "current_ltv": current_ltv,
            "btc_to_buy": actual_btc_to_buy,
            "cash_needed": cash_used,
            "can_fully_rebalance": can_fully_rebalance,
            "new_btc_total": new_btc_total,
            "new_ltv": new_ltv,
            "cash_used": cash_used,
            "cash_remaining": state.remaining_cash - cash_used,
            "total_cash_required": total_cash_required,
            "total_btc_needed": total_btc_needed
        }

def calculate_price_drop(initial_price: float, current_price: float) -> float:
    """Calculate percentage price drop from initial price."""
    return ((initial_price - current_price) / initial_price) * 100

def main():
    st.set_page_config(
        page_title="Bitcoin Loan Calculator",
        page_icon="₿",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for dark mode compatibility
    st.markdown("""
        <style>
        :root {
            /* Light mode colors */
            --primary-color: #E694FF;
            --background-color: #FFFFFF;
            --secondary-background-color: #F0F2F6;
            --text-color: #000000;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                /* Dark mode colors */
                --primary-color: #E694FF;
                --background-color: #0E1117;
                --secondary-background-color: #262730;
                --text-color: #FAFAFA;
            }
        }
        body {
            background-color: var(--background-color);
            color: var(--text-color);
        }
        .main {
            padding: 2rem;
        }
        .stButton button {
            width: 100%;
        }
        .info-box {
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        .metric-card {
            background-color: var(--secondary-background-color);
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-color);
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("₿ Bitcoin-Backed Loan Calculator")
    st.markdown("""
    <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 0.5rem; margin-bottom: 2rem;'>
        Calculate and simulate Bitcoin-backed loan scenarios with real-time price tracking and rebalancing calculations.
    </div>
    """, unsafe_allow_html=True)

    # Initial Loan Setup in a card-like container
    st.markdown("""
        <div style='background-color: var(--background-color); padding: 2rem; border-radius: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <h2>📊 Initial Loan Setup</h2>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        btc_amount = st.number_input(
            "Initial Bitcoin Collateral (BTC)",
            min_value=0.0,
            value=1.0,
            step=0.1,
            format="%.6f"
        )

        price_source = st.radio(
            "Select Initial Price Source:",
            ("Manual", "Live Price"),
            horizontal=True
        )
        
        if price_source == "Live Price":
            initial_price = BitcoinLoanCalculator.get_live_price()
            if initial_price is None:
                initial_price = 20000.0
                st.warning("⚠️ Could not fetch live price. Using default value.")
        else:
            initial_price = st.number_input(
                "Initial Bitcoin Price (€)",
                min_value=0.0,
                value=20000.0,
                step=100.0,
                format="%.2f"
            )

    with col2:
        ltv_ratio = st.slider(
            "Initial LTV Ratio (%)",
            min_value=30.0,
            max_value=50.0,
            value=50.0,
            step=0.1,
            help="Loan-to-Value ratio determines the maximum loan amount based on collateral value"
        )

        collateral_value = btc_amount * initial_price
        loan_amount = collateral_value * (ltv_ratio / 100)
        
        st.markdown("""
            <div style='background-color: #e6f3ff; padding: 1rem; border-radius: 0.5rem;'>
                <h3 style='color: #0066cc;'>📊 Initial Loan Summary</h3>
                <ul style='list-style-type: none; padding: 0;'>
                    <li>💶 Collateral Value: €{:,.2f}</li>
                    <li>💰 Loan Amount: €{:,.2f}</li>
                    <li>💵 Initial Cash Available: €{:,.2f}</li>
                </ul>
            </div>
        """.format(collateral_value, loan_amount, loan_amount), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Create initial loan state
    loan_state = LoanState(
        btc_collateral=btc_amount,
        price=initial_price,
        ltv_ratio=ltv_ratio,
        loan_amount=loan_amount,
        initial_cash=loan_amount,
        remaining_cash=loan_amount
    )

    st.markdown("---")

    # First Rebalancing Scenario
    st.markdown("""
        <div style='background-color: var(--background-color); padding: 2rem; border-radius: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <h2>🔄 First Rebalancing Scenario</h2>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        ltv_trigger_1 = st.number_input(
            "LTV Trigger for First Rebalance (%)",
            min_value=0.0,
            max_value=100.0,
            value=70.0,
            step=0.1
        )

        price_source_1 = st.radio(
            "Select Price Source for Scenario 1:",
            ("Manual", "Live Price", "Price at 70% LTV"),
            horizontal=True
        )

        if price_source_1 == "Live Price":
            price_1 = BitcoinLoanCalculator.get_live_price() or 15000.0
        elif price_source_1 == "Price at 70% LTV":
            price_1 = loan_amount / (loan_state.btc_collateral * 0.70)
        else:
            price_1 = st.number_input(
                "Bitcoin Price for Scenario 1 (€)",
                min_value=0.0,
                value=15000.0,
                step=100.0
            )

        # Calculate price drop
        price_drop_1 = calculate_price_drop(initial_price, price_1)

    with col2:
        rebalance_1 = BitcoinLoanCalculator.calculate_rebalance(
            loan_state,
            price_1,
            ltv_trigger_1
        )

        st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>
                <h4>📉 Price Change</h4>
                <p>Price Drop from Initial: {price_drop_1:.2f}%</p>
                <p>Current Price: €{price_1:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)

        if rebalance_1["needs_rebalance"]:
            st.warning(f"""
                🔄 **Rebalancing Needed**
                - Current LTV: {rebalance_1["current_ltv"]:.2f}%
                - Total Cash Required: €{rebalance_1["total_cash_required"]:,.2f}
                - Cash Available: €{loan_state.remaining_cash:,.2f}
            """)
            
            if not rebalance_1["can_fully_rebalance"]:
                st.error(f"""
                    ⚠️ **Insufficient Cash for Full Rebalancing!**
                    - Maximum BTC Possible to Buy: {rebalance_1["btc_to_buy"]:.6f} BTC
                    - Using Remaining Cash: €{rebalance_1["cash_used"]:,.2f}
                    - Additional Cash Needed: €{(rebalance_1["total_cash_required"] - loan_state.remaining_cash):,.2f}
                """)
            else:
                st.success(f"""
                    ✅ **Full Rebalancing Possible**
                    - BTC to Buy: {rebalance_1["btc_to_buy"]:.6f} BTC
                    - Cash to Use: €{rebalance_1["cash_used"]:,.2f}
                    - Cash Remaining After: €{rebalance_1["cash_remaining"]:,.2f}
                """)
        else:
            st.success(f"✅ No rebalancing needed. Current LTV: {rebalance_1['current_ltv']:.2f}%")

    st.markdown("</div>", unsafe_allow_html=True)

    # Update loan state for second scenario
    if rebalance_1["needs_rebalance"]:
        loan_state = LoanState(
            btc_collateral=rebalance_1["new_btc_total"],
            price=price_1,
            ltv_ratio=ltv_ratio,
            loan_amount=loan_amount,
            initial_cash=loan_amount,
            remaining_cash=rebalance_1["cash_remaining"]
        )

    st.markdown("---")

    # Second Rebalancing Scenario with similar styling
    st.markdown("""
        <div style='background-color: var(--background-color); padding: 2rem; border-radius: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <h2>🔄 Second Rebalancing Scenario</h2>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    proceed = False
    with col1:
        ltv_trigger_2 = st.number_input(
            "LTV Trigger for Second Rebalance (%)",
            min_value=0.0,
            max_value=100.0,
            value=65.0,
            step=0.1
        )

        price_source_2 = st.radio(
            "Select Price Source for Scenario 2:",
            ("Manual", "Live Price", "Price at 70% LTV", "Price at 65% LTV"),
            horizontal=True
        )

        if price_source_2 == "Live Price":
            price_2 = BitcoinLoanCalculator.get_live_price() or 10000.0
        elif price_source_2 == "Price at 70% LTV":
            price_2 = loan_amount / (loan_state.btc_collateral * 0.70)
        elif price_source_2 == "Price at 65% LTV":
            price_2 = loan_amount / (loan_state.btc_collateral * 0.65)
        else:
            price_2 = st.number_input(
                "Bitcoin Price for Scenario 2 (€)",
                min_value=0.0,
                value=10000.0,
                step=100.0
            )

        # Calculate price drop
        price_drop_2 = calculate_price_drop(initial_price, price_2)

    with col2:
        st.markdown(f"""
            <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>
                <h4>📉 Price Change</h4>
                <p>Price Drop from Initial: {price_drop_2:.2f}%</p>
                <p>Current Price: €{price_2:,.2f}</p>
            </div>
        """, unsafe_allow_html=True)

        rebalance_2 = BitcoinLoanCalculator.calculate_rebalance(
            loan_state,
            price_2,
            ltv_trigger_2
        )

        if rebalance_2["needs_rebalance"]:
            st.warning(f"""
                🔄 **Rebalancing Needed**
                - Current LTV: {rebalance_2["current_ltv"]:.2f}%
                - Total Cash Required: €{rebalance_2["total_cash_required"]:,.2f}
                - Cash Available: €{loan_state.remaining_cash:,.2f}
            """)

            if not rebalance_2["can_fully_rebalance"]:
                st.error(f"""
                    ⚠️ **Insufficient Cash for Full Rebalancing!**
                    - Maximum BTC Possible to Buy: {rebalance_2["btc_to_buy"]:.6f} BTC
                    - Using Remaining Cash: €{rebalance_2["cash_used"]:,.2f}
                    - Additional Cash Needed: €{(rebalance_2["total_cash_required"] - loan_state.remaining_cash):,.2f}
                """)

                proceed = st.checkbox("✔️ Proceed with rebalancing using all remaining cash?")
                if proceed:
                    loan_state = LoanState(
                        btc_collateral=rebalance_2["new_btc_total"],
                        price=price_2,
                        ltv_ratio=ltv_ratio,
                        loan_amount=loan_amount,
                        initial_cash=loan_state.initial_cash,
                        remaining_cash=rebalance_2["cash_remaining"]
                    )
                    st.success(f"""
                        ✅ **Rebalancing Done Using All Remaining Cash**
                        - BTC Bought: {rebalance_2["btc_to_buy"]:.6f} BTC
                        - Cash Used: €{rebalance_2["cash_used"]:,.2f}
                        - New BTC Total: {rebalance_2["new_btc_total"]:.6f} BTC
                        - New LTV: {rebalance_2["new_ltv"]:.2f}%
                    """)
            else:
                st.success(f"""
                    ✅ **Full Rebalancing Possible**
                    - BTC to Buy: {rebalance_2["btc_to_buy"]:.6f} BTC
                    - Cash to Use: €{rebalance_2["cash_used"]:,.2f}
                    - Cash Remaining After: €{rebalance_2["cash_remaining"]:,.2f}
                """)
                loan_state = LoanState(
                    btc_collateral=rebalance_2["new_btc_total"],
                    price=price_2,
                    ltv_ratio=ltv_ratio,
                    loan_amount=loan_amount,
                    initial_cash=loan_state.initial_cash,
                    remaining_cash=rebalance_2["cash_remaining"]
                )
        else:
            st.success(f"✅ No rebalancing needed. Current LTV: {rebalance_2['current_ltv']:.2f}%")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    # Third Section: Additional Rebalancing Options with improved UI
    if rebalance_2["needs_rebalance"] and not rebalance_2["can_fully_rebalance"] and proceed:
        st.markdown("""
            <div style='background-color: var(--background-color); padding: 2rem; border-radius: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <h2>📊 Critical Price Levels and Rebalancing Options</h2>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        with col1:
            # Price at 70% LTV section
            btc_collateral = loan_state.btc_collateral
            price_at_70_ltv = loan_state.loan_amount / (btc_collateral * 0.70)
            price_drop_70 = calculate_price_drop(initial_price, price_at_70_ltv)

            st.markdown("""
                <div style='background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>
                    <h3 style='color: #856404;'>⚠️ Price at 70% LTV</h3>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                - Bitcoin Price: €{price_at_70_ltv:,.2f}
                - Price Drop from Initial: {price_drop_70:.2f}%
            """)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("### 📈 Target LTV Scenarios")
            st.markdown("Purchase requirements to reach safer LTV levels:")

            for target_ltv in [65, 60, 55]:
                btc_needed = (loan_state.loan_amount / (price_at_70_ltv * (target_ltv / 100))) - btc_collateral
                euro_value_needed = btc_needed * price_at_70_ltv
                # Calculate BTC price at target LTV without buying more BTC
                price_at_target_ltv = loan_state.loan_amount / (btc_collateral * (target_ltv / 100))
                price_drop_target = calculate_price_drop(initial_price, price_at_target_ltv)
                
                st.markdown(f"""
                    <div style='background-color: var(--secondary-background-color); padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem;'>
                        <h4>Target LTV: {target_ltv}%</h4>
                        <ul style='list-style-type: none; padding-left: 0;'>
                            <li>🔹 BTC Needed: {btc_needed:.6f} BTC</li>
                            <li>🔹 Euro Value: €{euro_value_needed:,.2f}</li>
                            <li>🔹 Bitcoin Price: €{price_at_target_ltv:,.2f}</li>
                            <li>🔹 Price Drop from Initial: {price_drop_target:.2f}%</li>
                        </ul>
                    </div>
                """, unsafe_allow_html=True)

        with col2:
            # Price at 80% LTV and Liquidation Scenario
            price_at_80_ltv = loan_state.loan_amount / (btc_collateral * 0.80)
            price_drop_80 = calculate_price_drop(initial_price, price_at_80_ltv)
            btc_to_sell = loan_state.loan_amount / price_at_80_ltv
            btc_remaining = btc_collateral - btc_to_sell
            euro_value_sold = btc_to_sell * price_at_80_ltv
            euro_value_remaining = btc_remaining * price_at_80_ltv

            st.markdown("""
                <div style='background-color: #f8d7da; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>
                    <h3 style='color: #721c24;'>⚠️ Liquidation Scenario at 80% LTV</h3>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
                **Price Metrics:**
                - Bitcoin Price: €{price_at_80_ltv:,.2f}
                - Price Drop from Initial: {price_drop_80:.2f}%

                **Liquidation Impact:**
                - BTC Sold to Repay Loan: {btc_to_sell:.6f} BTC
                - Value of Sold BTC: €{euro_value_sold:,.2f}
                - BTC Remaining: {btc_remaining:.6f} BTC
                - Value of Remaining BTC: €{euro_value_remaining:,.2f}
            """)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.header("💫 Final Position Summary")

    # Final Summary with improved styling
    st.markdown("""
        <div style='background-color: #d4edda; padding: 1.5rem; border-radius: 1rem; margin-top: 2rem;'>
            <h3 style='color: #155724;'>📊 Final Position Summary</h3>
            <ul style='list-style-type: none; padding-left: 0;'>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
                <li>💎 Total BTC Collateral: {loan_state.btc_collateral:.6f} BTC</li>
                <li>💰 Current Collateral Value: €{loan_state.collateral_value:,.2f}</li>
                <li>💵 Remaining Cash: €{loan_state.remaining_cash:,.2f}</li>
                <li>📊 Current LTV: {(loan_state.loan_amount / loan_state.collateral_value * 100):.2f}%</li>
                <li>💳 Initial Cash Used: €{(loan_state.initial_cash - loan_state.remaining_cash):,.2f}</li>
    """, unsafe_allow_html=True)
    
    st.markdown("""
            </ul>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
