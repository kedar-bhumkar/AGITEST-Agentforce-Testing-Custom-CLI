#!/usr/bin/env python3
"""
agent_chat.py — Interactive Salesforce Agentforce Agent API client.

Reads credentials and config from a .env file, opens a session, and
lets you chat with the agent from the terminal.

.env keys used:
    SF_AGENT_API_CONSUMER_KEY    — External Client App consumer key
    SF_AGENT_API_CONSUMER_SECRET — External Client App consumer secret
    SF_INSTANCE_URL              — e.g. https://myorg.my.salesforce.com
    AGENT_BOT_ID                 — BotDefinition Id (0xb...)
    AGENT_TOPIC                  — (optional) topic DeveloperName to pre-select
    CONTEXT_VARS                 — (optional) JSON object of context variables
                                    e.g. {"MockPayloadType":"ExpressLane","$Context.Internal_Id":"123"}

Usage:
    python agent_chat.py              # uses .env in current directory
    python agent_chat.py my.env       # uses a specific env file
    python agent_chat.py --utterance "Hello"   # single-shot mode, no loop
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


# ── .env loader ──────────────────────────────────────────────────────────────

def load_env(path=".env"):
    """Parse a bash-style .env file (supports 'export KEY=value' and 'KEY=value')."""
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # strip leading 'export '
            line = re.sub(r"^export\s+", "", line)
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'\"")   # remove surrounding quotes
            env[key] = val
    return env


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http(method, url, body=None, headers=None, token=None):
    """Minimal HTTP helper. Returns (status_code, parsed_json_or_None)."""
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers:
        hdrs.update(headers)

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_token(instance_url, consumer_key, consumer_secret):
    """Client Credentials flow → access token string."""
    token_url = f"{instance_url}/services/oauth2/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": consumer_key,
        "client_secret": consumer_secret,
    }).encode()

    req = urllib.request.Request(
        token_url, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body)
            raise RuntimeError(
                f"OAuth failed — {err.get('error','?')}: {err.get('error_description', body[:200])}"
            )
        except json.JSONDecodeError:
            raise RuntimeError(f"OAuth HTTP {e.code}: {body[:200]}")

    token = result.get("access_token", "")
    if not token:
        raise RuntimeError(f"No access_token in OAuth response: {result}")
    return token


# ── Agent API calls ───────────────────────────────────────────────────────────

AGENT_API_BASE = "https://api.salesforce.com/einstein/ai-agent/v1"


def create_session(agent_bot_id, token, instance_url, topic=None, context_vars=None):
    """Create an agent session. Returns session_id."""
    url = f"{AGENT_API_BASE}/agents/{agent_bot_id}/sessions"

    body = {
        "externalSessionKey": str(uuid.uuid4()),
        "instanceConfig": {"endpoint": instance_url},
        "streamingCapabilities": {"chunkTypes": ["Text"]},
        "bypassUser": True,
    }

    # Context variables (injected at session creation)
    if context_vars:
        body["variables"] = [
            {"name": k, "type": "Text", "value": str(v)}
            for k, v in context_vars.items()
        ]

    status, resp = http("POST", url, body=body, token=token)

    if status not in (200, 201):
        raise RuntimeError(f"Session creation failed ({status}): {resp}")

    session_id = None
    if isinstance(resp, dict):
        session_id = (
            resp.get("sessionId")
            or resp.get("id")
            or (resp.get("session") or {}).get("id")
        )
    if not session_id:
        raise RuntimeError(f"No sessionId in response: {resp}")

    return session_id


def send_message(session_id, utterance, token, sequence=1):
    """Send a message to the agent. Returns the agent's reply text."""
    url = f"{AGENT_API_BASE}/sessions/{session_id}/messages"

    body = {
        "message": {
            "sequenceId": sequence,
            "type": "Text",
            "text": utterance,
        },
        "variables": [],
    }

    status, resp = http("POST", url, body=body, token=token)

    if status not in (200, 201):
        raise RuntimeError(f"Message send failed ({status}): {resp}")

    # Extract reply text
    reply = ""
    if isinstance(resp, dict):
        messages = resp.get("messages", [])
        for msg in messages:
            for item in msg.get("message", []):
                if item.get("type") == "Text":
                    reply += item.get("text", "")
        if not reply:
            # fallback paths different API versions use
            reply = (
                resp.get("text")
                or resp.get("message", {}).get("text", "")
                or json.dumps(resp, indent=2)
            )
    elif isinstance(resp, str):
        reply = resp

    return reply.strip()


def close_session(session_id, token):
    """DELETE the session."""
    url = f"{AGENT_API_BASE}/sessions/{session_id}"
    try:
        http("DELETE", url, token=token)
    except Exception:
        pass  # best-effort


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # ── Parse args ────────────────────────────────────────────────────────────
    single_utterance = None
    env_file = ".env"
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--utterance", "-u") and i + 1 < len(args):
            single_utterance = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            env_file = args[i]
            i += 1
        else:
            i += 1

    # ── Load .env ─────────────────────────────────────────────────────────────
    env = load_env(env_file)

    consumer_key    = env.get("SF_AGENT_API_CONSUMER_KEY", "")
    consumer_secret = env.get("SF_AGENT_API_CONSUMER_SECRET", "")
    instance_url    = env.get("SF_INSTANCE_URL", "").rstrip("/")
    agent_bot_id    = env.get("AGENT_BOT_ID", "")
    topic           = env.get("AGENT_TOPIC", "") or None

    # Context variables: JSON object in .env
    context_vars = {}
    raw_ctx = env.get("CONTEXT_VARS", "")
    if raw_ctx:
        try:
            context_vars = json.loads(raw_ctx)
        except json.JSONDecodeError:
            print(f"  WARNING: CONTEXT_VARS is not valid JSON — ignoring. Value: {raw_ctx[:80]}")

    # ── Validate required fields ───────────────────────────────────────────────
    missing = []
    if not consumer_key:    missing.append("SF_AGENT_API_CONSUMER_KEY")
    if not consumer_secret: missing.append("SF_AGENT_API_CONSUMER_SECRET")
    if not instance_url:    missing.append("SF_INSTANCE_URL")
    if not agent_bot_id:    missing.append("AGENT_BOT_ID")
    if missing:
        print(f"\n  ERROR: Missing required .env keys: {', '.join(missing)}")
        print(f"  Add them to '{env_file}' and try again.\n")
        sys.exit(1)

    # ── Banner ────────────────────────────────────────────────────────────────
    print()
    print("  Agentforce Agent Chat")
    print("  " + "─" * 50)
    print(f"  Org:   {instance_url}")
    print(f"  Agent: {agent_bot_id}")
    if topic:         print(f"  Topic: {topic}")
    if context_vars:  print(f"  Ctx:   {context_vars}")
    print()

    # ── OAuth ─────────────────────────────────────────────────────────────────
    print("  Authenticating...", end=" ", flush=True)
    try:
        token = get_token(instance_url, consumer_key, consumer_secret)
    except RuntimeError as e:
        print(f"\n  ERROR: {e}\n")
        sys.exit(1)
    print("OK")

    # ── Session ───────────────────────────────────────────────────────────────
    print("  Creating session...", end=" ", flush=True)
    try:
        session_id = create_session(
            agent_bot_id, token, instance_url,
            topic=topic, context_vars=context_vars or None,
        )
    except RuntimeError as e:
        print(f"\n  ERROR: {e}\n")
        sys.exit(1)
    print(f"OK  (session: {session_id})")
    print()

    # ── Single-shot mode ───────────────────────────────────────────────────────
    if single_utterance:
        print(f"  You: {single_utterance}")
        try:
            reply = send_message(session_id, single_utterance, token)
        except RuntimeError as e:
            print(f"  ERROR: {e}")
            close_session(session_id, token)
            sys.exit(1)
        print(f"\n  Agent: {reply}\n")
        close_session(session_id, token)
        return

    # ── Interactive loop ───────────────────────────────────────────────────────
    print("  Type your message and press Enter. Type 'quit' or 'exit' to end.\n")
    seq = 1
    while True:
        try:
            utterance = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not utterance:
            continue
        if utterance.lower() in ("quit", "exit", "q"):
            break

        try:
            reply = send_message(session_id, utterance, token, sequence=seq)
            seq += 1
        except RuntimeError as e:
            print(f"  ERROR: {e}")
            break

        print(f"\n  Agent: {reply}\n")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    print("  Closing session...", end=" ", flush=True)
    close_session(session_id, token)
    print("done.\n")


if __name__ == "__main__":
    main()
