# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/ai_provider.py
"""
Multi-Provider AI Completion
================================
Real, working implementation — not a seam. Every function in
ecclesia/api/ai_assistant_api.py already calls _call_ai(prompt, system_prompt),
which imports get_ai_completion from exactly this module path, so nothing
else needs to change for the AI Assistant to start working once you add at
least one API key below.

── SETUP ────────────────────────────────────────────────────────────────
Add whichever provider(s) you want to use to site_config.json. Never commit
API keys to source control — site_config.json is server-local and already
gitignored by Frappe convention. From the bench directory:

    bench --site [your-site] set-config anthropic_api_key "sk-ant-..."
    bench --site [your-site] set-config openai_api_key "sk-..."
    bench --site [your-site] set-config deepseek_api_key "sk-..."
    bench --site [your-site] set-config gemini_api_key "AIza..."

Optionally set a default provider (otherwise tries Anthropic first, then
falls through the others in order until one is configured):

    bench --site [your-site] set-config ai_default_provider "anthropic"

Optionally override the model per provider (defaults are set below and are
reasonable as of this writing, but model names change over time — check
each provider's docs if a call starts failing with a "model not found"
error):

    bench --site [your-site] set-config anthropic_model "claude-sonnet-4-5-20250929"
    bench --site [your-site] set-config openai_model "gpt-4o-mini"
    bench --site [your-site] set-config deepseek_model "deepseek-chat"
    bench --site [your-site] set-config gemini_model "gemini-1.5-flash"
─────────────────────────────────────────────────────────────────────────
"""

import frappe
import requests

PROVIDER_ORDER = ["anthropic", "openai", "deepseek", "gemini"]

DEFAULT_MODELS = {
	"anthropic": "claude-sonnet-4-5-20250929",
	"openai": "gpt-4o-mini",
	"deepseek": "deepseek-chat",
	"gemini": "gemini-1.5-flash",
}


class _ProviderNotConfigured(Exception):
	pass


def get_ai_completion(prompt, system_prompt=None, provider=None, max_tokens=1024):
	"""
	Try the requested/default provider first, then fall through the rest of
	PROVIDER_ORDER so a single missing key or a transient provider outage
	doesn't take down every AI Assistant feature at once.
	"""
	order = _provider_order(provider)
	last_error = None

	for p in order:
		try:
			return _call_provider(p, prompt, system_prompt, max_tokens)
		except _ProviderNotConfigured:
			continue
		except Exception as e:
			frappe.log_error(
				title=f"AI Provider ({p}) call failed",
				message=frappe.get_traceback(),
			)
			last_error = f"{p}: {e}"
			continue

	frappe.throw(
		f"No AI provider could complete the request. Configure at least one of "
		f"anthropic_api_key / openai_api_key / deepseek_api_key / gemini_api_key "
		f"in site_config.json (see docstring in ecclesia/utils/ai_provider.py for "
		f"the exact bench commands). Last error: {last_error or 'no provider configured'}"
	)


def _provider_order(provider):
	if provider and provider in PROVIDER_ORDER:
		return [provider] + [p for p in PROVIDER_ORDER if p != provider]
	default = frappe.conf.get("ai_default_provider")
	if default and default in PROVIDER_ORDER:
		return [default] + [p for p in PROVIDER_ORDER if p != default]
	return list(PROVIDER_ORDER)


def _call_provider(provider, prompt, system_prompt, max_tokens):
	api_key = frappe.conf.get(f"{provider}_api_key")
	if not api_key:
		raise _ProviderNotConfigured(provider)

	model = frappe.conf.get(f"{provider}_model") or DEFAULT_MODELS[provider]
	dispatch = {
		"anthropic": _call_anthropic,
		"openai": _call_openai,
		"deepseek": _call_deepseek,
		"gemini": _call_gemini,
	}
	return dispatch[provider](prompt, system_prompt, max_tokens, api_key, model)


# ═══════════════════════════════════════════════════════════════════════════════
#  PROVIDER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _call_anthropic(prompt, system_prompt, max_tokens, api_key, model):
	resp = requests.post(
		"https://api.anthropic.com/v1/messages",
		headers={
			"x-api-key": api_key,
			"anthropic-version": "2023-06-01",
			"content-type": "application/json",
		},
		json={
			"model": model,
			"max_tokens": max_tokens,
			"system": system_prompt or "",
			"messages": [{"role": "user", "content": prompt}],
		},
		timeout=60,
	)
	resp.raise_for_status()
	data = resp.json()
	return "".join(
		block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
	).strip()


def _call_openai(prompt, system_prompt, max_tokens, api_key, model):
	messages = []
	if system_prompt:
		messages.append({"role": "system", "content": system_prompt})
	messages.append({"role": "user", "content": prompt})

	resp = requests.post(
		"https://api.openai.com/v1/chat/completions",
		headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
		json={"model": model, "messages": messages, "max_tokens": max_tokens},
		timeout=60,
	)
	resp.raise_for_status()
	data = resp.json()
	return data["choices"][0]["message"]["content"].strip()


def _call_deepseek(prompt, system_prompt, max_tokens, api_key, model):
	# DeepSeek's API is OpenAI-compatible.
	messages = []
	if system_prompt:
		messages.append({"role": "system", "content": system_prompt})
	messages.append({"role": "user", "content": prompt})

	resp = requests.post(
		"https://api.deepseek.com/chat/completions",
		headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
		json={"model": model, "messages": messages, "max_tokens": max_tokens},
		timeout=60,
	)
	resp.raise_for_status()
	data = resp.json()
	return data["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt, system_prompt, max_tokens, api_key, model):
	url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
	payload = {
		"contents": [{"role": "user", "parts": [{"text": prompt}]}],
		"generationConfig": {"maxOutputTokens": max_tokens},
	}
	if system_prompt:
		payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

	resp = requests.post(url, json=payload, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	return data["candidates"][0]["content"]["parts"][0]["text"].strip()
