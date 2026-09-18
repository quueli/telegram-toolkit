# telegram-toolkit

![ci](https://github.com/quueli/telegram-toolkit/actions/workflows/ci.yml/badge.svg)

bits i keep reusing in telethon projects.

**session_pool**: a directory of authorised .session files, handed out one at a time. `acquire()` fails fast, `acquire_or_wait()` queues. proxies rotate round robin. a session that hit FloodWait is parked until it expires, and after a batch of work a session rests for 15-25 min *before* it gets anywhere near the limit, which in practice means it never hits it.

**keyword_matcher**: is this message about any of my keywords. russian snowball stemming so дизайнер/дизайна/дизайну count as one word, fuzzy match for typos, multi-word keywords need every word present.

**rate_limit**: jittered delays, retry with backoff for transient errors, and two exceptions that let a long batch bail out of a FloodWait *with* the partial results instead of loosing an hour of work.

**reports**: rows -> html / xlsx / txt (the txt one splits itself when it gets too big for telegram).

    pip install -r requirements.txt
    python -m examples.discover     # runs against a fake client, no account needed
    pytest

for real use put .session files in SESSION_DIR and set API_ID / API_HASH.
