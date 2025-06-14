import streamlit as st
import matplotlib.pyplot as plt
from engine import MartingaleEngine, SessionState

def display_streak_info(engine):
    """Displays data-driven, professional warnings about winning and losing streaks."""
    s = engine.s

    # --- Handle Loss Streaks ---
    if s.loss_streak >= 3:
        next_bet = engine.next_bet()
        bankroll = s.bankroll
        bet_percentage = (next_bet / bankroll) * 100 if bankroll > 0 else 0

        # For a fair game, win probability is 1/payout. Loss probability is 1 - win_prob.
        loss_prob = 1 - (1 / s.payout)
        # Probability of the *entire sequence* happening (e.g., 4 losses in a row)
        next_streak_prob = (loss_prob ** (s.loss_streak + 1)) * 100

        if s.loss_streak == 3:
            st.warning(f"""
            **⚠️ 3 Derrotas Consecutivas. Próxima Aposta: {next_bet:.2f} €**

            Está a entrar numa sequência crítica. Esta aposta compromete **{bet_percentage:.1f}%** da sua banca.
            
            A probabilidade de uma 4ª derrota seguida é de **{next_streak_prob:.2f}%**.
            
            *Mantenha o plano — o risco aumenta exponencialmente.*
            """)
        elif s.loss_streak == 4:
            st.error(f"""
            **🚨 Ponto de Inflexão: 4 Derrotas. Próxima Aposta: {next_bet:.2f} €**

            A aposta atual representa **{bet_percentage:.1f}%** da sua banca.
            
            A probabilidade de uma 5ª derrota seguida é de **{next_streak_prob:.2f}%**.
            
            *Reveja a sua estratégia e o seu limite de perdas.*
            """)
        elif s.loss_streak >= 5:
            st.error(f"""
            **🚨 Alerta Máximo: {s.loss_streak} Derrotas. Próxima Aposta: {next_bet:.2f} €**

            Esta aposta consome **{bet_percentage:.1f}%** da sua banca restante.
            
            A probabilidade de mais uma derrota é de **{next_streak_prob:.2f}%**.
            
            *Recomenda-se vivamente que pare para reavaliar a sua exposição ao risco.*
            """)
    
    # --- Handle Win Streaks ---
    elif s.win_streak >= 3:
        initial_bankroll = st.session_state.history[0]
        current_bankroll = s.bankroll
        gain_percentage = ((current_bankroll - initial_bankroll) / initial_bankroll) * 100 if initial_bankroll > 0 else 0
        
        st.success(f"""
        **📈 {s.win_streak} Vitórias Consecutivas.**

        O seu saldo está **{gain_percentage:+.1f}%** acima do valor inicial.
        
        Aposta seguinte mantém-se: **{s.base_bet:.2f} €**.

        *A sorte favorece os disciplinados — continue a seguir o plano.*
        """)

st.set_page_config(page_title="Martingale Engine", layout="centered")
st.title("🎲 SIMULAI")

# --- Main Interface (session active and not over) ---
if 'engine' in st.session_state and not st.session_state.get('session_over'):
    engine = st.session_state.engine
    s = engine.s

    # Display feedback message from the last action
    if 'message' in st.session_state:
        msg_type, msg_text = st.session_state.message
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)
        del st.session_state.message  # Clear after displaying

    st.header(f"Next Bet: {engine.next_bet():.2f} €")
    st.metric("Current Bankroll", f"{s.bankroll:.2f} €", f"{s.bankroll - st.session_state.history[0]:+.2f} €")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ I Won", use_container_width=True):
            engine.record_result(True)
            st.session_state.history.append(s.bankroll)
            st.session_state.message = ("success", "🎉 Great win! The next bet is reset to the base amount.")
            st.rerun()
    with col2:
        if st.button("❌ I Lost", use_container_width=True):
            try:
                engine.record_result(False)
                st.session_state.history.append(s.bankroll)
                st.session_state.message = ("warning", "Tough luck. The next bet has been doubled.")
            except RuntimeError:
                st.session_state.session_over = True
            st.rerun()

    if len(st.session_state.history) > 1:
        fig, ax = plt.subplots()
        ax.plot(st.session_state.history)
        st.pyplot(fig)

    display_streak_info(engine)

    st.info(f"Base Bet: {s.base_bet}€ | Payout: {s.payout}x | Loss Streak: {s.loss_streak}/{s.max_loss_streak}")
    if st.button("Reset Session"):
        for key in ['engine', 'history', 'session_over']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# --- Setup / Session Over Screen ---
else:
    # Display session over info if applicable
    if st.session_state.get('session_over'):
        s = st.session_state.engine.s
        st.header("🚨 Session Over")
        st.error(f"Stop-loss of {s.max_loss_streak} consecutive losses reached.")
        
        final_bankroll = st.session_state.history[-1]
        initial_bankroll = st.session_state.history[0]
        st.metric("Final Bankroll", f"{final_bankroll:.2f} €", f"{final_bankroll - initial_bankroll:+.2f} €")

        if len(st.session_state.history) > 1:
            fig, ax = plt.subplots()
            ax.plot(st.session_state.history)
            ax.set_title("Bankroll History")
            ax.set_xlabel("Round"); ax.set_ylabel("Bankroll (€)")
            st.pyplot(fig)
        
        st.info("Analyze the session and start a new one with adjusted parameters if you wish.")
        
        # Get previous values to pre-fill the form
        prev_bank = final_bankroll if final_bankroll > 0 else 10.0
        prev_base_bet = s.base_bet
        prev_payout = s.payout
        prev_max_loss = s.max_loss_streak
        
    else:
        st.subheader("Setup New Session")
        # Default values for a brand new session
        prev_bank = 1000.0
        prev_base_bet = 1.0
        prev_payout = 2.0
        prev_max_loss = 8

    # The setup form
    st.subheader("Session Parameters")
    starting_bank = st.number_input("Banca Inicial (€)", 0.0, 1_000_000.0, prev_bank, 100.0)
    base_bet = st.number_input("Aposta Base (€)", 0.1, 10_000.0, prev_base_bet, 0.1)
    payout = st.number_input("Payout (e.g., 2.0 for 1:1)", 1.01, 100.0, prev_payout, 0.01)
    max_loss_streak = st.slider("Max Loss Streak (Stop-Loss)", 1, 20, prev_max_loss)

    if st.button("Start Session 🚀"):
        # Clear old state before starting
        for key in ['engine', 'history', 'session_over']:
            if key in st.session_state: del st.session_state[key]
            
        state = SessionState(bankroll=starting_bank, base_bet=base_bet, payout=payout, max_loss_streak=max_loss_streak)
        st.session_state.engine = MartingaleEngine(state)
        st.session_state.history = [state.bankroll]
        st.rerun()
