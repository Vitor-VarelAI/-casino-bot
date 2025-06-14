# engine.py
from dataclasses import dataclass, field
from collections import deque
from typing import Deque

@dataclass
class SessionState:
    bankroll: float         # dinheiro disponível
    base_bet: float         # aposta mínima definida pelo utilizador
    payout: float           # ex.: 2.0 em vermelho/preto roleta europeia
    max_loss_streak: int    # protecção contra bancarrota
    current_bet: float = 0.0
    loss_streak: int = 0
    win_streak: int = 0
    outcome_history: Deque[bool] = field(default_factory=lambda: deque(maxlen=20))

    def __post_init__(self):
        self.current_bet = self.base_bet

class MartingaleEngine:
    def __init__(self, state: SessionState):
        self.s = state

    def next_bet(self):
        """Devolve a aposta que o utilizador deve colocar agora."""
        return self.s.current_bet

    def record_result(self, won: bool):
        """Actualiza estado depois do utilizador indicar win/lose."""
        self.s.outcome_history.append(won)
        if won:
            gain = self.s.current_bet * (self.s.payout - 1)
            self.s.bankroll += gain
            self.s.current_bet = self.s.base_bet
            self.s.loss_streak = 0
            self.s.win_streak += 1
        else:
            self.s.bankroll -= self.s.current_bet
            self.s.loss_streak += 1
            self.s.win_streak = 0
            if self.s.loss_streak > self.s.max_loss_streak:
                raise RuntimeError("Stop‑loss atingido — termina a sessão!")
            self.s.current_bet = min(
                self.s.base_bet * 2 ** self.s.loss_streak,
                self.s.bankroll          # nunca apostar mais do que existe
            )

if __name__ == "__main__":
    s = SessionState(bankroll=1000, base_bet=1, payout=2, max_loss_streak=10)
    engine = MartingaleEngine(s)

    # Simulação manual
    for _ in range(20):
        bet = engine.next_bet()
        print(f"Aposta agora: {bet:.2f} € | Banca: {s.bankroll:.2f} €")
        if s.bankroll <= 0 or bet <= 0:
            print("Banca quebrada ou aposta inválida. Fim da sessão.")
            break
        resultado = input("Ganhei (g) / Perdi (p)? ")
        engine.record_result(resultado.lower().startswith("g"))
