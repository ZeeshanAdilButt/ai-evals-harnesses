"""The shipped scrubber: replace emails and phone numbers before a ticket is stored or sent."""
import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE = re.compile(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{2,4}[\s.-]?\d{2,4}\b")


def scrub_text(text: str) -> str:
    text = EMAIL.sub("[email]", text)
    return PHONE.sub("[phone]", text)
