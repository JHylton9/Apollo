"""The JCF wanted-persons registry as structured records, rebuilt from Docling output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from docling_core.types.doc.document import DoclingDocument

from apollo.retrieval.tables import load_document

WANTED_JSON = "JCF-Wanted_Persons.json"

# Offences as printed in the registry, longest first so "Attempted Murder" is not read
# as "Murder", with spellings Docling's OCR produced ("Frau ulent").
_OFFENCES = {
    r"attempted murder": "Attempted Murder",
    r"murder\s*(?:&amp;|&|and)\s*wounding with intent": "Murder and Wounding with Intent",
    r"murder": "Murder",
    r"assault at common law(?:\s*\(knife and gun\))?": "Assault at Common Law",
    r"wounding with intent": "Wounding with Intent",
    r"frau\s?d?ulent conversion": "Fraudulent Conversion",
}
_OFFENCE = "(?P<offence>" + "|".join(_OFFENCES) + ")"
# A name is two or three capitalised words; "Wanted F(o|a)r" tolerates the OCR slip.
_NAME = r"(?P<name>[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){1,2}?)"
_ALIAS = r"(?:\s+OTHERWISE CALLED\s+'(?P<alias>[^']+)')?"
_ENTRY = re.compile(_NAME + _ALIAS + r"\s+(?i:wanted\s+f[ao]r:?)\s+(?i:" + _OFFENCE + r")")
_OFFENCE_ONLY = re.compile(r"^(?i:wanted\s+f[ao]r:?)\s+(?i:" + _OFFENCE + r")")
_ALIAS_ONLY = re.compile(_NAME + r"\s+OTHERWISE CALLED\s+'(?P<alias>[^']+)'")
# The citizen reporting numbers printed on every registry page.
_TIP_LINES = {
    "Police Emergency": re.compile(r"Emergency\s+(\d{3})"),
    "Crime Stop": re.compile(r"Crime Stop\s+(\d{3})"),
    "Tip Line": re.compile(r"Tip Line\s+(\d{3}-\d{3}-\d{4})"),
}


@dataclass
class WantedPerson:
    name: str
    offence: str
    aliases: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)


def _canonical_offence(text: str) -> str:
    for pattern, name in _OFFENCES.items():
        if re.fullmatch(pattern, text.strip(), flags=re.I):
            return name
    return text.strip()


def parse_wanted_persons(doc: DoclingDocument) -> list[WantedPerson]:
    people: dict[str, WantedPerson] = {}

    def add(name: str, offence: str, alias: str | None, page: int | None) -> None:
        key = " ".join(name.split()).title()
        person = people.setdefault(key, WantedPerson(key, _canonical_offence(offence)))
        # Prefer the most specific offence seen, e.g. "Murder and Wounding with Intent".
        if len(_canonical_offence(offence)) > len(person.offence):
            person.offence = _canonical_offence(offence)
        if alias and alias.title() not in person.aliases:
            person.aliases.append(alias.title())
        if page and page not in person.pages:
            person.pages.append(page)

    items = list(doc.texts)
    for index, item in enumerate(items):
        page = item.prov[0].page_no if item.prov else None
        for match in _ENTRY.finditer(item.text):
            add(match["name"], match["offence"], match["alias"], page)
        # A heading such as "JEVAUGHN CAMPBELL" followed by "Wanted for Murder ...".
        only = _OFFENCE_ONLY.match(item.text)
        previous = items[index - 1] if index else None
        if only and previous is not None and str(previous.label) == "section_header":
            if re.fullmatch(r"[A-Z][A-Z'\-]+(?:\s+[A-Z][A-Z'\-]+){1,2}", previous.text):
                add(previous.text, only["offence"], None, page)
    # Second pass: captions like "RAHEEM BROWN OTHERWISE CALLED 'BERGER'" name an alias
    # without the offence; attach it only to someone already found above.
    for item in items:
        for match in _ALIAS_ONLY.finditer(item.text):
            person = people.get(" ".join(match["name"].split()).title())
            if person and match["alias"].title() not in person.aliases:
                person.aliases.append(match["alias"].title())
    return sorted(people.values(), key=lambda p: p.name)


def parse_tip_lines(doc: DoclingDocument) -> dict[str, str]:
    text = " ".join(item.text for item in doc.texts)
    found = {}
    for label, pattern in _TIP_LINES.items():
        if match := pattern.search(text):
            found[label] = match.group(1)
    return found


class RegistryStore:
    def __init__(self, docling_dir: Path) -> None:
        self.docling_dir = docling_dir

    @cached_property
    def _document(self) -> DoclingDocument:
        path = self.docling_dir / WANTED_JSON
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing; run `uv run apollo ingest --pipeline docling` first."
            )
        return load_document(path)

    @cached_property
    def wanted(self) -> list[WantedPerson]:
        return parse_wanted_persons(self._document)

    @cached_property
    def tip_lines(self) -> dict[str, str]:
        return parse_tip_lines(self._document)
