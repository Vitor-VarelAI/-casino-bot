import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, CallbackQueryHandler, ConversationHandler

from engine import MartingaleEngine, SessionState
from bacbo_handler import bacbo_start, bacbo_choose_bet, bacbo_exit, CHOOSE_BET

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

# --- Keyboards ---
def get_start_menu_keyboard() -> InlineKeyboardMarkup:
    """Creates the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📈 Martingale Advisor", callback_data="menu_martingale")],
        [InlineKeyboardButton("🎲 Bac Bo", callback_data="menu_bacbo")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_game_keyboard() -> InlineKeyboardMarkup:
    """Creates the 'I Won'/'I Lost' keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("I Won ✅", callback_data='won'),
            InlineKeyboardButton("I Lost ❌", callback_data='lost')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with a game selection menu."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Welcome to GaleBot. Please choose a game:",
        reply_markup=get_start_menu_keyboard(),
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
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    # Handle menu selections first
    if query.data == "menu_martingale":
        martingale_instructions = (
            "<b>Martingale Advisor</b>\n\n"
            "To start a game, use the <code>/play</code> command.\n\n"
            "You can optionally set your starting bankroll and base bet:\n"
            "<code>/play [bankroll] [base_bet]</code>\n\n"
            "<b>Example:</b> <code>/play 200 5</code>\n\n"
            "Use <code>/stop</code> to end your game."
        )
        await query.edit_message_text(text=martingale_instructions, parse_mode='HTML')
        return

    if query.data == "menu_bacbo":
        await query.edit_message_text(
            text="🎲 You've selected <b>Bac Bo</b>!\n\nUse the /bacbo command to start playing.",
            parse_mode='HTML'
        )
        return

    # --- Handle 'won'/'lost' for the Martingale game ---
    user = update.effective_user
    if 'engine' not in context.user_data:
        await query.edit_message_text(text="Your game session has expired or was stopped. Please start a new game with /play.")
        return

    engine: MartingaleEngine = context.user_data['engine']
    won = query.data == 'won'

    try:
        last_bet = engine.s.current_bet
        engine.record_result(won)
        state = engine.s

        # Check for game over conditions after the result is recorded
        if state.bankroll <= 0:
            await query.edit_message_text(text=f"Last Round: You {'WON' if won else 'LOST'} a bet of {last_bet:.2f}.\n\nGame over! Your bankroll is depleted. Use /stop to clear.")
            del context.user_data['engine']
            return
        
        if engine.next_bet() > state.bankroll:
             await query.edit_message_text(text=f"Last Round: You {'WON' if won else 'LOST'} a bet of {last_bet:.2f}.\n\nGame over! Your next bet is larger than your bankroll. Use /stop to clear.")
             del context.user_data['engine']
             return

        outcome_text = "WON" if won else "LOST"
        message = (
            f"Last Round: You {outcome_text} a bet of {last_bet:.2f}.\n"
            f"New Bankroll: {state.bankroll:.2f} | Loss Streak: {state.loss_streak}\n\n"
            f"Your next bet is: {engine.next_bet():.2f}\n\n"
            f"Place the bet and report the result below."
        )
        await query.edit_message_text(text=message, reply_markup=get_game_keyboard())

    except RuntimeError as e:
        # This catches the stop-loss from the engine
        await query.edit_message_text(text=f"🛑 Stop-Loss Triggered! 🛑\n{e}\n\nYour session has been stopped.")
        del context.user_data['engine']
        logger.info(f"Game session stopped for user {user.id}.")
        await update.message.reply_text("Your game session has been stopped and all progress cleared.")
    else:
        await update.message.reply_text("You don't have an active game session to stop.")


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

    # --- Bac Bo Conversation Handler ---
    bacbo_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('bacbo', bacbo_start)],
        states={
            CHOOSE_BET: [
                CallbackQueryHandler(bacbo_choose_bet, pattern='^bacbo_(player|banker)$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(bacbo_exit, pattern='^bacbo_exit$'),
            CommandHandler('stop', bacbo_exit) # Also allow /stop to exit
        ],
    )
    application.add_handler(bacbo_conv_handler)

    # Add the main button handler with a specific pattern to avoid conflicts
    # This should come AFTER specific handlers like the one for Bac Bo
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(menu_martingale|menu_bacbo|won|lost)$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting... Press Ctrl-C to stop.")
    application.run_polling()
    logger.info("Bot has stopped.")

if __name__ == "__main__":
    main()
