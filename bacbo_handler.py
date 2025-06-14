from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bacbo_engine import BacBoEngine, BacBoSessionState

# States for ConversationHandler
CHOOSE_BET, AWAITING_RESULT = range(2)

def get_bacbo_keyboard() -> InlineKeyboardMarkup:
    """Creates the 'Player'/'Banker'/'Tie' keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("Player", callback_data='bacbo_player'),
            InlineKeyboardButton("Banker", callback_data='bacbo_banker'),
            InlineKeyboardButton("Tie", callback_data='bacbo_tie')
        ],
        [InlineKeyboardButton("Exit Game", callback_data='bacbo_exit')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def bacbo_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the Bac Bo game flow."""
    await update.message.reply_text(
        "Welcome to Bac Bo! Please choose your bet:",
        reply_markup=get_bacbo_keyboard()
    )
    return CHOOSE_BET

async def bacbo_choose_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's choice of Player, Banker, or Tie."""
    query = update.callback_query
    await query.answer()

    user_choice = query.data.split('_')[1]  # 'player', 'banker', or 'tie'

    # Initialize engine if it doesn't exist
    if 'bacbo_engine' not in context.user_data:
        context.user_data['bacbo_engine'] = BacBoEngine(BacBoSessionState())
    
    engine: BacBoEngine = context.user_data['bacbo_engine']
    result = engine.play_round(user_choice)

    player_dice_str = f"🎲{result['player_dice'][0]} + 🎲{result['player_dice'][1]}"
    banker_dice_str = f"🎲{result['banker_dice'][0]} + 🎲{result['banker_dice'][1]}"

    message_parts = [
        f"Your choice: <b>{result['user_choice'].capitalize()}</b>",
        f"Player rolls: {player_dice_str} = <b>{result['player_score']}</b>",
        f"Banker rolls: {banker_dice_str} = <b>{result['banker_score']}</b>",
        ""
    ]

    outcome = result['outcome_type']
    payout_ratio = result['payout_ratio']

    if outcome == 'win':
        message_parts.append(f"🎉 You WON! The winner was {result['winner'].capitalize()}. Pays 1:1.")
    elif outcome == 'loss':
        message_parts.append(f"😔 You LOST. The winner was {result['winner'].capitalize()}.")
    elif outcome == 'tie_player_banker':
        message_parts.append(f"⚖️ It's a TIE! Since you bet on {result['user_choice'].capitalize()}, 90% of your bet is returned.")
    elif outcome == 'tie_win':
        tie_sum = result['player_score'] # or banker_score, they are equal in a tie
        payout_desc = result['tie_sum_payout_description']
        message_parts.append(f"🎉 You WON by betting on Tie! A Tie on sum {tie_sum} pays {payout_desc}.")
    else:
        message_parts.append("An unexpected game outcome occurred.")

    message_parts.append("\nChoose your next bet:")
    final_message = "\n".join(message_parts)

    await query.edit_message_text(
        text=final_message,
        reply_markup=get_bacbo_keyboard(),
        parse_mode='HTML'
    )
    return CHOOSE_BET

async def bacbo_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exits the Bac Bo game, handling both command and button exits."""
    message = "You have exited the Bac Bo game. Use /start to see the menu again."
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(message)
    elif update.message:
        await update.message.reply_text(message)

    if 'bacbo_engine' in context.user_data:
        del context.user_data['bacbo_engine']
    return ConversationHandler.END
