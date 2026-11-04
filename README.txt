# 📦 Telegram File + Website Hosting Bot (Termux)

Doosri bot files **aur** websites host karta hai. Reply-keyboard menu, subscription system, QR payment, channel approval — sab kuch. Kabhi sleep nahi hota.

## ✨ Features
- 🔒 **Force Channel Join** — join na karne par error + "Joined" verify.
- ⌨️ **Reply Keyboard menu** (inline nahi) — neeche fixed buttons.
- 📤 **Upload File** → bot file (.py/.js/.sh) host + auto-run.
- 🌐 **Host Website** → koi bhi file; **.zip auto-unzip**; website host; **public link** milta hai.
- 📂 **Check File / 🗂 Files** → Start/Stop/Restart/Delete/Log/Get + website manage.
- 👤 **Profile** → name, subscription status, usage/limit.
- 💎 **Buy Subscription** → 12 Days ₹39 · 1 Month ₹59 · 1 Year ₹99 · Lifetime ₹199 (admin se editable).
  - Plan click → **QR** (admin-set) + UPI `Devendra3289@fam` → user **UTR** bhejta hai
  - Request **payment channel** me jaati hai → admin **Accept/Reject**
  - Accept → subscription utne din ke liye active, expire hone par auto-off.
- 🚦 **Limits** — Free user: **3 bots + 3 websites**. Subscribed: **unlimited** (jab tak plan).
- 🔧 **/admin panel** — force channels, payment channel, prices, QR, folders, files block/unblock, stats.
- ♻️ **Never Sleeps** — watchdog auto-restart + infinity polling.

---

## 🚀 Termux Setup

```bash
pkg update && pkg upgrade -y
pkg install python nodejs git -y
pip install pyTelegramBotAPI

# Website ka PUBLIC link banane ke liye (zaroori) — koi ek:
pkg install cloudflared -y          # best (free quick tunnel)
# agar cloudflared na mile to localtunnel apne aap npx se chalega (nodejs zaroori)

python bot.py
```

> ⚠️ **cloudflared / localtunnel ke bina** website sirf local link (`http://ip:port`) par chalegi, public open nahi hogi. Public link ke liye cloudflared install karna best hai.

### 🔋 24/7 (sleep na ho)
```bash
termux-wake-lock
nohup python bot.py > out.log 2>&1 &
# ya tmux:
pkg install tmux -y
tmux new -s bot
python bot.py        # detach: Ctrl+b d   |  wapas: tmux attach -t bot
```
Phone settings → Battery → Termux ko **Don't optimize** karein.

---

## ⚙️ Pehli baar admin setup (`/admin`)
1. **Add Channel** → force-join channel (bot ko us channel me **admin** banayein).
2. **Set Payment Channel** → jahan payment requests aayengi (bot ko admin banayein).
3. **Set QR** → payment QR photo bhejein.
4. **Edit Prices** → chahein to plan prices change karein.

## 💳 Payment flow (user)
Buy Subscription → plan chunein → QR/UPI par pay karein → **UTR/Transaction ID** bhejein → admin channel me Accept dabaye → subscription active. Reject → active nahi hota.

## 📁 Folders
- `hosted_files/` — bot files · `hosted_sites/` — websites · `logs/` — logs
- `config.json` — channels/prices/QR/payment-channel · `users.json` — users & subscriptions

## 🔑 Pre-set
- BOT TOKEN, ADMIN ID (`7227172211`), UPI (`Devendra3289@fam`) `bot.py` me set hain.
