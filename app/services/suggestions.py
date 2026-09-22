"""Curated starter prompts; no model call or credentials are needed."""

# Localized punctuation is intentional.
# ruff: noqa: RUF001

from typing import Literal

SuggestionLocale = Literal["en-US", "zh-CN", "ja-JP"]

_PROMPTS: dict[SuggestionLocale, tuple[str, ...]] = {
    "en-US": (
        "Help me compare products before buying.",
        "What should I check before placing an order?",
        "Explain how streaming AI responses work.",
    ),
    "zh-CN": (
        "帮我比较商品，看看哪款更适合我。",
        "下单前需要确认哪些信息？",
        "解释一下 AI 流式回复是怎么实现的。",
    ),
    "ja-JP": (
        "自分に合う商品を選べるよう、比較を手伝ってください。",
        "注文前に確認しておくことはありますか？",
        "AI の回答が少しずつ表示される仕組みを教えてください。",
    ),
}


def get_suggestions(locale: SuggestionLocale) -> list[str]:
    return list(_PROMPTS[locale])
