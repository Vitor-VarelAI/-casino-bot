import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

@dataclass
class BacBoSessionState:
    """Holds the state for a single Bac Bo game session."""
    choice: str = ""  # 'player', 'banker', or 'tie'
    history: List[str] = field(default_factory=list)  # List of 'win', 'loss', 'tie_player_banker', 'tie_win'
    # We are not tracking bet amounts or bankroll yet for Bac Bo

class BacBoEngine:
    """Manages the logic for a Bac Bo game."""

    TIE_PAYOUTS: Dict[int, int] = {
        2: 88, 12: 88,
        3: 25, 11: 25,
        4: 10, 10: 10,
        5: 6,  9: 6,
        6: 4,  8: 4,
        7: 4
    }

    def __init__(self, state: BacBoSessionState):
        self.s = state

    def play_round(self, user_choice: str) -> Dict[str, Any]:
        """
        Simulates a round of Bac Bo.
        - Rolls two dice for Player and two for Banker.
        - Determines the winner based on Bac Bo rules.
        - Returns a dictionary with the results, including payout implications.
        """
        self.s.choice = user_choice.lower()

        player_dice1 = random.randint(1, 6)
        player_dice2 = random.randint(1, 6)
        player_score = player_dice1 + player_dice2

        banker_dice1 = random.randint(1, 6)
        banker_dice2 = random.randint(1, 6)
        banker_score = banker_dice1 + banker_dice2

        winner: str
        outcome_type: str # 'win', 'loss', 'tie_player_banker', 'tie_win'
        payout_ratio: float = 0.0
        tie_sum_payout: int = 0

        if player_score > banker_score:
            winner = "player"
            if self.s.choice == "player":
                outcome_type = "win"
                payout_ratio = 1.0 # Pays 1:1
            elif self.s.choice == "banker":
                outcome_type = "loss"
            else: # choice == 'tie'
                outcome_type = "loss"
        elif banker_score > player_score:
            winner = "banker"
            if self.s.choice == "banker":
                outcome_type = "win"
                payout_ratio = 1.0 # Pays 1:1
            elif self.s.choice == "player":
                outcome_type = "loss"
            else: # choice == 'tie'
                outcome_type = "loss"
        else: # Tie
            winner = "tie"
            if self.s.choice == "player" or self.s.choice == "banker":
                outcome_type = "tie_player_banker" # Bet on Player/Banker, result is Tie
                payout_ratio = 0.9 # 90% of stake returned
            elif self.s.choice == "tie":
                outcome_type = "tie_win" # Bet on Tie, result is Tie
                tie_sum_payout = self.TIE_PAYOUTS.get(player_score, 0) # player_score == banker_score in a tie
                payout_ratio = float(tie_sum_payout) # Pays X:1
            else:
                # Should not happen with valid choices
                outcome_type = "error"
        
        self.s.history.append(outcome_type)

        return {
            "player_score": player_score,
            "banker_score": banker_score,
            "player_dice": (player_dice1, player_dice2),
            "banker_dice": (banker_dice1, banker_dice2),
            "winner": winner,
            "user_choice": self.s.choice,
            "outcome_type": outcome_type,
            "payout_ratio": payout_ratio, # e.g., 1.0 for 1:1, 0.9 for 90% return, 88.0 for 88:1
            "tie_sum_payout_description": f"{tie_sum_payout}:1" if outcome_type == "tie_win" and tie_sum_payout > 0 else "N/A"
        }
