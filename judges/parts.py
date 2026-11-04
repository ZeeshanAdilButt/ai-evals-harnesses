"""The judge prompts for the criterion "states the refund policy correctly" (refund replies only).

v1: the bare criterion, pass or fail (lenient by design, for 5.1).
v2: v1 plus definitions and a fixed JSON output shape.
v3: all five parts: one criterion, definitions, labelled examples (set 1), a short reason before
    the verdict, and the fixed output shape. v3 is the canonical judge.
Builder id d{0,1}r{0,1}e{1,2,3}: definitions off or on, reason before the verdict off or on,
example set 1, 2 or 3; always one criterion and the fixed output shape. d1r1e1 is v3.
"""
from __future__ import annotations

CRITERION = "Does this reply state FreshMarket's refund policy correctly?"

DEFINITIONS = """A reply FAILS if any of these is true:
- it states a refund fact that the policy contradicts (for example a window other than 7 days, a refund to a different payment method, or a time other than 5 working days);
- it promises a refund, an amount or an action the policy does not allow (for example a full-order refund when one item is missing, or a delivery-fee refund for a delivery less than 2 hours late);
- it leaves out a step the policy requires for this case (asking for a photo of spoiled or damaged food before a refund, or sending a food safety case to a person the same day).
Otherwise the reply PASSES. A reply that states no refund fact at all passes if it promises nothing the policy forbids and leaves out no required step. Tone, length and style do not matter."""

EXAMPLES = {
    1: [
        ("My strawberries arrived mouldy yesterday, refund please.",
         "So sorry about the strawberries! Please send us a photo of them and we will refund them to your original payment method within 5 working days. FreshMarket Support",
         "Asks for the photo and states the refund method and time correctly.", "pass"),
        ("My strawberries arrived mouldy yesterday, refund please.",
         "So sorry! I have refunded your strawberries; the money will be back within 24 hours. FreshMarket Support",
         "Skips the photo the policy requires and states the wrong refund time.", "fail"),
        ("The milk was missing from my order.",
         "Sorry the milk was missing. Missing items are refunded in full with no return needed, back to your original payment method within 5 working days. FreshMarket Support",
         "Every refund fact matches the policy.", "pass"),
        ("The milk was missing from my order, refund everything.",
         "Very sorry! I have refunded your whole order as a goodwill gesture. FreshMarket Support",
         "Promises a full-order refund the policy does not allow; only the missing item is refunded.", "fail"),
    ],
    2: [
        ("My delivery was 3 hours late.",
         "Sorry for the wait. Because it was more than 2 hours late, we refund the delivery fee to your original payment method. FreshMarket Support",
         "Correct rule for late deliveries.", "pass"),
        ("My delivery was 1 hour late, I want the fee back.",
         "Sorry for the delay! I have refunded your delivery fee. FreshMarket Support",
         "Refunds a fee the policy allows only after 2 hours.", "fail"),
        ("Where is my refund from last week?",
         "Refunds go back to your original payment method within 5 working days, so it should arrive soon. FreshMarket Support",
         "States the refund time and method correctly.", "pass"),
        ("The bread was stale when it came 10 days ago.",
         "Sorry about the bread! Send a photo and we will refund it. FreshMarket Support",
         "Offers a refund outside the 7-day window.", "fail"),
    ],
    3: [
        ("My son ate the yogurt and now has hives.",
         "I am so sorry. I am passing this to a member of our team today, who will contact you. If symptoms get worse, call a doctor. FreshMarket Support",
         "Sends the food safety case to a person the same day, as the policy requires.", "pass"),
        ("My son ate the yogurt and now has hives.",
         "Sorry to hear that! I have refunded the yogurt. FreshMarket Support",
         "Decides a refund instead of sending the food safety case to a person.", "fail"),
        ("Can I change my password?",
         "Yes, you can change it in the app under Account Settings. FreshMarket Support",
         "States no refund fact and promises nothing the policy forbids.", "pass"),
        ("The eggs were cracked, delivered yesterday.",
         "Sorry about the eggs. I will refund them to your FreshMarket wallet right away. FreshMarket Support",
         "Wrong refund method (wallet instead of the original payment method) and no photo asked for.", "fail"),
    ],
}

SHAPE_REASON = 'Reply with one JSON object and nothing else: {"reason": "<one short sentence>", "verdict": "pass" or "fail"}.'
SHAPE_PLAIN = 'Reply with one JSON object and nothing else: {"verdict": "pass" or "fail"}.'


def examples_text(n: int, reverse: bool, reason: bool) -> str:
    ex = EXAMPLES[n][::-1] if reverse else EXAMPLES[n]
    out = []
    for i, (t, r, why, v) in enumerate(ex, 1):
        body = f'{{"reason": "{why}", "verdict": "{v}"}}' if reason else f'{{"verdict": "{v}"}}'
        out.append(f"Example {i}\nTicket: {t}\nReply: {r}\nAnswer: {body}")
    return "Labelled examples:\n\n" + "\n\n".join(out)


def judge_prompt(judge_id: str, reverse: bool = False) -> str:
    """judge_id: v1, v2, v3 or a builder id such as d0r1e2. reverse puts the examples in reverse order."""
    if judge_id == "v1":
        return f"You grade support replies for FreshMarket, an online grocery store.\n\n{CRITERION} Answer with one word: pass or fail."
    if judge_id == "v2":
        return f"You grade support replies for FreshMarket, an online grocery store.\n\nCriterion: {CRITERION}\n\n{DEFINITIONS}\n\n{SHAPE_PLAIN}"
    if judge_id == "v3":
        judge_id = "d1r1e1"
    d, r, e = int(judge_id[1]), int(judge_id[3]), int(judge_id[5])
    parts = ["You grade support replies for FreshMarket, an online grocery store.", f"Criterion: {CRITERION}"]
    if d:
        parts.append(DEFINITIONS)
    parts.append(examples_text(e, reverse, bool(r)))
    parts.append(SHAPE_REASON if r else SHAPE_PLAIN)
    return "\n\n".join(parts)


ALL_JUDGES = ["v1", "v2", "v3"] + [f"d{d}r{r}e{e}" for d in (0, 1) for r in (0, 1) for e in (1, 2, 3) if (d, r, e) != (1, 1, 1)]
