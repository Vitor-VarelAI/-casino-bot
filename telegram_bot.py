import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler

from engine import MartingaleEngine, SessionState

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables! Please set it in your .env file.")
    exit()

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and instructions when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"""Hi {user.mention_html()}! Welcome to the Martingale Bot.

To start a game, use the <b>/play</b> command.

You can optionally set your starting bankroll and base bet like this:
<code>/play [bankroll] [base_bet]</code>

<b>Example:</b> <code>/play 200 5</code> (starts with a 200 bankroll and a 5 base bet).

If you just use <code>/play</code>, it will start with defaults (100 bankroll, 1 base bet).

Use <b>/stop</b> to end your current game at any time.""",
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    logger.info(f"User {update.effective_user.id} sent message: {update.message.text}")
    await update.message.reply_text(update.message.text)


def get_game_keyboard() -> InlineKeyboardMarkup:
    """Returns the InlineKeyboardMarkup for the game (Won/Lost buttons)."""
    keyboard = [
        [InlineKeyboardButton("I Won ✅", callback_data='won'), InlineKeyboardButton("I Lost ❌", callback_data='lost')]
    ]
    return InlineKeyboardMarkup(keyboard)


async def play_command(update: Update, context: CallbackContext) -> None:
    """Starts a new game or shows the current bet amount."""
    user = update.effective_user
    logger.info(f"User {user.first_name} ({user.id}) initiated /play command with args: {context.args}")

    # Case 1: A game is already in progress.
    if 'engine' in context.user_data:
        if context.args:  # User tried to start a new game with params while one is active
            await update.message.reply_text(
                "You already have a game in progress. Please use /stop before starting a new one."
            )
            return

        # Continue the existing game by showing the current bet
        engine: MartingaleEngine = context.user_data['engine']
        state: SessionState = engine.s

        if state.bankroll <= 0 or state.current_bet > state.bankroll:
            await update.message.reply_text("Game over! Your bankroll is depleted. Use /stop to clear or /play to start a new game.")
            del context.user_data['engine']
            return

        bet_amount = engine.next_bet()
        message = (
            f"Bankroll: {state.bankroll:.2f} | Loss Streak: {state.loss_streak}\n\n"
            f"Your next bet is: {bet_amount:.2f}\n\n"
            f"Place the bet and report the result below."
        )
        await update.message.reply_text(message, reply_markup=get_game_keyboard())
        return

    # Case 2: No game in progress. Create a new one.
    bankroll = 100.0
    base_bet = 1.0
    try:
        if len(context.args) >= 1:
            bankroll = float(context.args[0])
        if len(context.args) >= 2:
            base_bet = float(context.args[1])
        if len(context.args) > 2:
            await update.message.reply_text("Too many arguments. Please use `/play [bankroll] [base_bet]`.")
            return
        if bankroll <= 0 or base_bet <= 0:
            await update.message.reply_text("Bankroll and base bet must be positive numbers.")
            return
        if base_bet > bankroll:
            await update.message.reply_text("Base bet cannot be greater than your bankroll.")
            return
    except ValueError:
        await update.message.reply_text(
            "Invalid input. Please provide numbers for bankroll and base bet.\nExample: `/play 200 5`"
        )
        return

    initial_state = SessionState(bankroll=bankroll, base_bet=base_bet, payout=2.0, max_loss_streak=8)
    context.user_data['engine'] = MartingaleEngine(initial_state)
    
    # Get the newly created engine and state
    engine = context.user_data['engine']
    state = engine.s
    bet_amount = engine.next_bet()

    # Combine the "new game" message with the first bet suggestion
    message = (
        f"New game started!\n"
        f"Initial Bankroll: {state.bankroll:.2f} | Base Bet: {state.base_bet:.2f}\n\n"
        f"Your first bet is: {bet_amount:.2f}\n\n"
        f"Place the bet and report the result below."
    )
    await update.message.reply_text(message, reply_markup=get_game_keyboard())


async def button_handler(update: Update, context: CallbackContext) -> None:
    """Handles button presses for win/loss reporting."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    user = query.from_user
    if 'engine' not in context.user_data:
        await query.edit_message_text(text="Your game session has expired or was stopped. Use /play to start a new one.")
        return

    engine: MartingaleEngine = context.user_data['engine']
    state: SessionState = engine.s

    # Determine if the user won or lost from the button press
    won = query.data == 'won'
    outcome_text = "WON" if won else "LOST"
    bet_amount = engine.next_bet()

    try:
        engine.record_result(won)
    except RuntimeError as e:
        await query.edit_message_text(text=f"🛑 STOP-LOSS HIT! {e}\nGame over. Use /play to start a new one.")
        del context.user_data['engine']
        return

    # Check for game over after the result is recorded
    if state.bankroll <= 0:
        await query.edit_message_text(text=f"You {outcome_text} the last round of {bet_amount:.2f}.\nYour bankroll is now empty. Game over!\nUse /play to start a new one.")
        del context.user_data['engine']
        return

    next_bet_amount = engine.next_bet()
    message = (
        f"Last Round: You {outcome_text} a bet of {bet_amount:.2f}.\n"
        f"New Bankroll: {state.bankroll:.2f} | Loss Streak: {state.loss_streak}\n\n"
        f"Your next bet is: {next_bet_amount:.2f}\n\n"
        f"Place the bet and report the result below."
    )

    await query.edit_message_text(text=message, reply_markup=get_game_keyboard())


async def stop_command(update: Update, context: CallbackContext) -> None:
    """Stops the current game session and clears user data."""
    user = update.effective_user
    if 'engine' in context.user_data:
        del context.user_data['engine']
        logger.info(f"Game session stopped for user {user.id}.")
        await update.message.reply_text("Your game session has been stopped and all progress cleared.")
    else:
        await update.message.reply_text("You don't have an active game session to stop.")

# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, context.error)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Register Handlers ---
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non-command i.e message - echo the message on Telegram
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting... Press Ctrl-C to stop.")
    application.run_polling()
    logger.info("Bot has stopped.")

if __name__ == "__main__":
    main()
