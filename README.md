# Beast

Set `BEAST_NAME=YourName` in `.env` and Beast greets you by name.

Your personal AI agent. Runs on your laptop, opens in your browser, talks to Claude through your own API key.

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY`.
3. Add your email accounts (as many as you like): `python main.py add-account` (Gmail needs an App Password). List with `python main.py accounts`.
4. `python server.py` opens Beast at http://127.0.0.1:8765. First time it asks you to create a PIN.
5. Start on every login: `python install_autostart.py`

## Studio: build anything
Open the **Studio** tab (or just ask in chat: "build a landing page for my bakery called Crumb").
- Describe it, optionally pick a type (landing page, website, web app, dashboard, game, tool, API) and a look, then press **Build it**.
- Beast plans the project with Claude, writes every file into `~/BeastProjects/<name>`, and shows the live preview while it works.
- Keep changing it in plain words ("make it dark and add a pricing section"). Every change is saved as a new version; **Undo last change** goes back.
- Switch between desktop, tablet and phone widths, read the code, open it in a new tab, or download it as a .zip.
- Static sites preview instantly. Node and Python apps get a **Run app** button: Beast shows you the exact commands first, then installs and starts them (Python apps get their own virtual environment) and previews the running app.
- Builds only ever create new folders, so nothing you already have is overwritten.
- Settings in `.env`: `BUILD_MAX_TOKENS`, `BEAST_WORKSPACE`, `BEAST_PREVIEW_PORT` (default 8766).
- Previews are served on their own port and sandboxed, and Beast's API rejects requests from any other port, so a generated page can't read your email or act as you.

## The Pack: many agents, one head
Open the **Pack** tab (or just ask in chat; Beast sends the pack by itself when a request has several parts).
- Describe one big job, for example "research three laptops under 60000, compare them, build a comparison page and draft an email to my dad with the pick".
- **The head** (the core in the middle) splits the job into parts and hands each part to an agent. Parts that don't depend on each other run at the same time, up to 4 at once (`BEAST_MAX_AGENTS`, 1 to 8). A part that needs another agent's result waits for it.
- You see every agent live: what it is doing right now, each step it took, which Claude model it is using, and what it brought back. **Stop the pack** stops everything.
- At the end the head writes one report. Anything that sends, posts, deletes or runs code is not done by the agents: it appears in the report as a request for you to approve or decline.
- **Built-in agents:** Scout (web research), Analyst (your files and numbers), Scribe (writing), Smith (builds in Studio), Courier (inbox, calendar, missions), Navigator (websites).
- **It learns:**
  - When a job needs a skill no agent has, the head makes a new agent and keeps it. You can also make one yourself: "Forge agent" on the Pack tab. Learned agents can be removed; built-in ones stay.
  - After each job an agent may keep one short lesson for next time (shown on its card). You can add lessons yourself ("Teach") or delete them.
  - **What Beast knows:** tell it how you like things done, on the Pack tab or in chat ("remember that I prefer short emails"). Every conversation and every agent reads these. It refuses to store passwords, PINs, card numbers and keys. Stored in `data/memory.json`; agents in `data/pack.json`; the last 30 runs in `data/runs.json`.
- Agents only get the tools listed for them, they cannot start other packs, and they follow the same rules as the chat.
- Cost: a pack run makes several Claude calls at once, so it uses more of your API credit than a single chat message.

## Claude models
- The model picker is in the header, in the chat and on the Pack tab. It lists every Claude model your API key can use (fetched live from the API, newest first), so new models appear by themselves.
- **Auto** (the default) picks per job: the fastest model for quick jobs (the Courier agent, short notes), the balanced one for chat, email sorting and most agents, and the strongest for building websites and apps. Today that is Haiku, Sonnet and Opus. Builds on the strongest model cost the most.
- Pick a specific model and Beast uses it for everything until you change it back.
- Optional `.env` overrides for what Auto uses: `FAST_MODEL`, `MODEL`, `BUILD_MODEL`.

## Posting on sites you're signed in to
- Sign in once: "open x.com so I can sign in". Beast opens the site in its own browser window and does nothing else. You type your password yourself; Beast never sees or types passwords. The sign-in is kept on your laptop in `data/browser-profile`.
- After that: "post on X: Shipping tonight". Beast shows you the exact words and the site, and posts only after you approve, once.
- A normal browsing task ("open example.com and find the cheapest laptop") cannot post or send anything: buttons like Post, Send, Submit and Comment are refused unless the task was approved as a posting task. Purchases, payments, deletions and password fields are always refused.
- Beast uses your installed Chrome if it has one, then Edge, then its own Chromium (`BEAST_BROWSER=chrome|msedge|chromium` to force one). It keeps a separate profile, so it does not touch your everyday browser's tabs or passwords.
- To use a Chrome window you started yourself, start Chrome with `--remote-debugging-port=9222` and a separate `--user-data-dir`, then set `BEAST_CDP_URL=http://127.0.0.1:9222`.
- Some sites detect automation, ask for extra checks or forbid bots in their terms; posting can fail there, and it is your account at risk. LinkedIn and Discord stay blocked for that reason (use your Discord bot for your own server).

## Using it
- **PIN:** asked every time you open Beast. Forgot it? `python server.py --reset-pin` (needs access to this computer).
- **Multiple inboxes:** the Brief covers all accounts; with more than one, each email shows its account label after the time.
- **Chat (💬):** opens a pop-up with all your saved conversations (data/chats.json). Start new ones, reopen old ones, delete them.
- **Build projects:** "build me a todo API in Flask". Beast proposes the folder and file list; on Approve it writes them to `~/BeastProjects/<name>` (never overwrites an existing folder).
- **Drafts:** Beast proposes a reply; on Approve it is saved to that account's Drafts folder. Beast never sends email.

## Email actions, Sheets and websites (ask in chat)
- **Any account you add** (`python main.py add-account`) can be used by name: "email my professor from College", "archive that promo", "mark the interview email read". Sending, archiving, trashing and marking read all show an approval card first.
- **Google Sheets:** "create a sheet in Work tracking my internship applications" creates it in that account and opens it in your browser straight away. Reading a sheet is automatic; editing an existing sheet asks first. One-time setup per account: create a Google Cloud OAuth client (type Desktop) with the Sheets API enabled, save it as `google_client.json` here, then run `python main.py google-login you@gmail.com`. Cells are written as plain values (no formulas).
- **Websites:** "open example.com and find the cheapest laptop". After you approve, a visible browser window opens and Beast clicks and types on that one site. Log in yourself when it pauses; your logins are kept in `data/browser-profile`. It refuses purchase/payment/delete buttons and password fields, and won't leave the site. One-time: `pip install playwright` then `playwright install chromium`. Set `BEAST_HEADLESS=1` to hide the window.
- Discord's web app is blocked on purpose (their terms forbid automating personal accounts).

## New in this version (all through the chat, no screen changes)
- **Calendar:** "what's my day?", "any clashes this week?", "add a call with Sam Friday 3-4pm, remind me 15 min before". Reading is automatic; adding an event asks first and warns about clashes. Run `python main.py google-login you@gmail.com` again once to grant calendar access (enable the Google Calendar API in your Cloud project too).
- **Scheduled tasks and the daily digest:** "give me a digest every weekday at 7:30". It runs by itself (read-only), posts to your chat history and sends a desktop notification. If the laptop was off at that time it catches up when you start it (within 12 hours). Set `BEAST_WATCHLIST=NIFTY,SENSEX,RELIANCE.NS` and `BEAST_NEWS_TOPICS=...` in `.env` for the markets and news sections. "What schedules do I have?" / "remove schedule abc123".
- **Price, change and stock watching:** "tell me when this laptop drops below 45000" (add `browser` for JavaScript-heavy shops), "alert me if TCS.NS goes above 4200". Checked in the background, alerts arrive as a notification plus a new chat.
- **Stocks:** quotes via Yahoo Finance's public endpoint (unofficial, can be delayed or change). Facts only, never investment advice.
- **Web search:** uses Claude's built-in search tool. It must be enabled for your Anthropic organisation in the Console.
- **Documents:** Beast now reads Excel, Word and PDF files (also inside folders) and can summarize long documents or web articles. "Create a Word playbook / PDF event plan" asks first, then saves to `~/BeastDocuments`.
- **Images:** "make a poster image of ..." asks first (it costs credit), using your own image service. Add `IMAGE_API_KEY` (OpenAI-style; override with `IMAGE_BASE_URL` / `IMAGE_MODEL`). Saved to `~/BeastImages`.
- **Run and fix code:** after Beast builds a project, "run the tests" proposes one plain command (python, pytest, pip, node, npm, npx, cargo, go, make) inside that project. You approve the exact command; it runs with a 2 minute limit and without your API keys, and the output comes back in the chat. "Fix it" proposes file edits you approve, then you rerun. Code you run has your normal permissions, so only approve commands you understand.
- **Browser stays open:** "open YouTube and play lofi, leave it open". Close it with "close the browser".
- **Discord bot (your own server):** create a bot, invite it, add `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` to `.env`. Then "draft an announcement for #events" and approve to post (no @everyone pings). Reading channels needs the bot's Message Content intent.
- **Startup music:** synthesized in the browser (no audio files), starts after you enter your PIN. Silence it with `BEAST_MUSIC=off` in `.env`. Browsers need a click first, which the PIN screen provides.
- **Voice input:** press Alt+V, speak, and it sends. Works in Chrome and Edge. No button was added.
- **LinkedIn and Discord websites are blocked** for the browser agent (their terms forbid automation). For LinkedIn use "Get a copy of your data" and let Beast read the export, job-alert emails, or paste text.

## Buttons and interface extras
- **🔊 Sound** (header and intro screen): mutes the startup music and the small effect sounds. Remembered between visits. `BEAST_MUSIC=off` in `.env` makes it start muted.
- **🎤 Speak** (next to Send, or Alt+V): dictate a request and it sends when you stop talking. **🔈** in the chat header reads replies aloud.
- **⌘ Command palette** (Ctrl/Cmd+K): search every tool, example prompt, tab and email, then run it.
- **🧰 Tools tab:** a card for each capability with example prompts that open the chat and run.
- **Sun/moon button** switches between dark and light.
- **Today timeline** (clashes glow red; tap an event to ask Beast about it) appears once Google Calendar is connected. **Market ticker** appears when `BEAST_WATCHLIST` is set.
- **The core:** a molten heart inside three golden rings. On the PIN screen it is a sealed dial that lights up as you type and spins free when the PIN is right. In the intro it ignites. On the Brief your emails orbit it (three orbits: worth your time, skim, ignore; hover an ember to see the email, click to open it). On the Pack tab it is the head.

## Safety
- Mail is read-only (nothing marked read). Files are only read, only inside your home folder, never hidden or config folders.
- Server listens on 127.0.0.1 only. PIN is stored as a salted hash; wrong PINs are rate-limited.
- Email, file and web page text is untrusted; Beast and its agents don't follow instructions hidden in it.
- Nothing is sent, posted, deleted or run without your approval, including inside a pack run.
- Emails and files you ask about are sent to the Anthropic API. Chats and email passwords are stored locally in plain files (data/, accounts.json), so keep this folder private.
