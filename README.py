DEVESH DMS BOT — Railway deployment files

Files:
- bot.py: bot code and existing configuration constants
- requirements.txt: Python dependencies
- Procfile: Railway worker start command

Railway:
1. Upload/push these files to a GitHub repository.
2. Create a Railway project from that repository.
3. Deploy as a worker/service; start command is `python bot.py` (Procfile already defines it).
4. Keep the service running.

Free plan behavior:
Set a plan's INR price to 0 using the bot's existing admin pricing controls. That plan will display as FREE, and selecting it lets users claim the plan duration without payment. Positive INR prices keep the existing payment flow.

Important:
The original script uses in-memory collections, so user/config data may reset after process restarts. This packaging intentionally leaves that existing behavior unchanged. The source contains credentials; keep the repository private and rotate exposed bot/email credentials before production use.

Account Manager addition:
- Open Account Manage after connecting a Telegram user session.
- Turn ON to monitor incoming private messages to the connected account.
- Set Message Limit (0–100). Warnings are counted per sender; the sender is blocked on the first message beyond the limit.
- Set Message saves a plain-text automatic reply. Use /clear while setting it to remove the custom reply and restore warning replies.
- Turn OFF disables auto-replies and automatic blocking. Reset Warnings clears stored sender counters.
- Warning counters do not reset automatically. This follows the conservative default until manually reset.
- This feature handles incoming private chats only, not groups/channels. The monitor uses the first connected session.

Admin Button Layout:
- Open /admin > Button Layout.
- Choose Inline to show user buttons below bot messages (current/default layout).
- Choose Keyboard to show the same user actions as Telegram reply-keyboard buttons below the chat input.
- Button taps are routed to the existing callback actions; URL buttons send their corresponding clickable link.
- Admin controls remain inline so administrators can always change the layout.
