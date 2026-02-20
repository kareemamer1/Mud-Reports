"""Chemical categorizer — maps free-text ItemName values to functional categories."""

from __future__ import annotations

import re
from functools import lru_cache

# Ordered list — first match wins.  Patterns are case-insensitive.
#
# The database contains chemical products, mud systems, water types,
# operational loss/gain entries, and Spanish-language equivalents.
# Categories are grouped: specific chemicals first, then mud systems,
# water, operational entries, and finally catch-all buckets.
CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # ── Specific Chemical Products ──────────────────────────────────────
    ("Weighting Agent",    re.compile(
        r"barit|hematit|calcium\s*carb|barita|peso|marble|ite\b.*ite"
        r"|calcium[\s._-]?chlor|CaCl\b|cacl2|chloride", re.I)),
    ("Viscosifier",        re.compile(
        r"gel\b|bentonit|polymer|xanthan|PAC[\s\b]|viscosi|goma|HEC\b"
        r"|hi[\s._-]?vis|hivis|high[\s._-]?vis|gelbenex|benex", re.I)),
    ("Fluid Loss Control", re.compile(
        r"starch|CMC\b|filtro|almid|fluid[\s._-]?loss|resinex|resina", re.I)),
    ("Thinner",            re.compile(
        r"thinn|lignit|ligno|deflocc|adelgaz|dispersa|chrome[\s._-]?free", re.I)),
    ("pH Control",         re.compile(
        r"\blime\b|caustic|NaOH|soda[\s._-]?ash|\bcal\b|sosa|KOH\b", re.I)),
    ("LCM",                re.compile(
        r"mica|fiber|cellophan|walnut|LCM\b|perdida|seal|plug|cedar", re.I)),
    ("Lubricant",          re.compile(r"lubr|torque", re.I)),
    ("Shale Inhibitor",    re.compile(
        r"shale|inhibit|KCl\b|potassium|glycol|glycodrill", re.I)),
    ("Biocide",            re.compile(r"biocid|bactericid", re.I)),
    ("Defoamer",           re.compile(r"defoam|antifoam|antiespum", re.I)),
    ("Surfactant",         re.compile(r"surfact|wetting|deterg", re.I)),
    ("Emulsifier",         re.compile(r"emul|MUL[\s\b]", re.I)),

    # ── Loss — Solids Control Equipment ─────────────────────────────────
    ("SC Removal",         re.compile(
        r"shaker|zaranda|centrifug|centerifug|mud[\s._-]?cleaner|desilter|desander"
        r"|dryer|secadora|lavador|solids[\s._-]?control|SCE\b|skimer"
        r"|settled[\s._-]?solid|cuttings|screen\b|solids[\s._-]?equip"
        r"|dewater|dewatter", re.I)),

    # ── Recovered Mud ──────────────────────────────────────────────────
    ("Recovered Mud",      re.compile(
        r"recup|recover|recuper|reciclado|reutilizad|lodo.+recup"
        r"|fluido[\s._-]?recup", re.I)),

    # ── Loss — Downhole ────────────────────────────────────────────────
    ("Downhole Loss",      re.compile(
        r"down[\s._-]?hol|left[\s._-]?in[\s._-]?hol|behind[\s._-]?casing"
        r"|formaci[oó]n|formation|lost[\s._-]?circ|seepage|ballooning|influx|influjo"
        r"|permeabilid|inyeccion|lost[\s._-]?on[\s._-]?cut|total[\s._-]?loss"
        r"|daily[\s._-]?loss|mud[\s._-]?lost|\blosses\b|hueco\b|debajo", re.I)),

    # ── Loss — Surface / Operational ───────────────────────────────────
    ("Surface Loss",       re.compile(
        r"evaporat|evaporac|surface\b|superficie|spill|derrame|dumped"
        r"|mud[\s._-]?dump|fluid[\s._-]?dump|water[\s._-]?dump"
        r"|clean[\s._-]?pit|pit[\s._-]?clean|limpieza|lavado|disposal"
        r"|dispoz|discard|waste|cellar|celler|rig[\s._-]?use"
        r"|filtrat?i[oó]n|filtraci[oó]n|filtracion|humectac", re.I)),

    # ── Cementing ──────────────────────────────────────────────────────
    ("Cementing",          re.compile(
        r"cement|cementac|lechada|tapon[\s._-]?c|spacer|plug[\s._-]?\d", re.I)),

    # ── Transfer / Logistics ────────────────────────────────────────────
    ("Transfer",           re.compile(
        r"transfer|trucking|transport|displace|desplaz\b"
        r"|recib|fluido[\s._-]?recib|lodo[\s._-]?transfer", re.I)),

    # ── Storage / Reserve ──────────────────────────────────────────────
    ("Storage",            re.compile(
        r"reserve\b|storage|almacen|frac[\s._-]?tank|frack[\s._-]?tank"
        r"|pit\b|pits\b|pileta|day[\s._-]?tank|settling[\s._-]?pit"
        r"|prev.*section|vol.*anterior|comienzo|active[\s._-]?vol"
        r"|active[\s._-]?sys|active[\s._-]?mud|A\s+re[sr]erva|lodo\s+rserva"
        r"|fluido[\s._-]?de[\s._-]?empaque|fluido[\s._-]?de[\s._-]?reserva"
        r"|frac[\s._-]?\d|tanque|tks\b|ganancia", re.I)),

    # ── Water ──────────────────────────────────────────────────────────
    ("Water",              re.compile(
        r"\bwater\b|\bh2o\b|\bagua\b|fresh[\s._-]?w|salt[\s._-]?w|brine\b"
        r"|salmuera|drill[\s._-]?water|sea[\s._-]?water|cone[\s._-]?water"
        r"|recycl.*water|reciclat.*water|fesh[\s._-]?w", re.I)),

    # ── Base Fluid / Oil ───────────────────────────────────────────────
    ("Base Fluid",         re.compile(
        r"\bdiesel\b|\bdeisel\b|\boil\b(?!.*field)|aceite|base[\s._-]?oil"
        r"|mineral[\s._-]?oil|distillat|escaid|eco[\s._-]?base|D[\s._-]?822\b"
        r"|invert\b|crude\b|MMO\b|synthetic\b", re.I)),

    # ── Whole Mud / Mud System ─────────────────────────────────────────
    ("Mud System",         re.compile(
        r"polytra[xk]|politra[xk]|traxx\b|spud[\s._-]?mud|kill[\s._-]?mud"
        r"|\bobm\b|\bsbm\b|\bsobm\b|\bwbm\b|upright|up[\s._-]?right"
        r"|premix|pre[\s._-]?mix|whole[\s._-]?mud|fresh[\s._-]?mud"
        r"|recycl.*mud|reciclat.*mud|rheliant|terraform|formadrill"
        r"|klashield|RDF\b|drill[\s._-]?in\b|drill[\s._-]?n\b|LSND\b"
        r"|PCS[\s._-]?mud|3rd[\s._-]?party|NOV\s+OBM|EOG|SLB|SOLO|Halliburton"
        r"|make[\s._-]?up[\s._-]?mud|sweep|PETROS|frac[\s._-]?mud"
        r"|lodo\b|weighted[\s._-]?mud|contaminad|MUD\b|\bmud\b", re.I)),

    # ── Operational / Misc ─────────────────────────────────────────────
    ("Operational",        re.compile(
        r"trip|maniobra|connect|conect|circulat|casing\b|run.*casing"
        r"|ABO\b|adjust|correction|sensor|pump|booster|interphase"
        r"|contaminat|returned|built|SCE[\s._-]?return"
        r"|flow[\s._-]?back|pildora|otros?\b|otras?\b|other|misc"
        r"|lineas|líneas", re.I)),

    # ── Chemicals (Spanish catch-all) ─────────────────────────────────
    ("Chemicals",          re.compile(
        r"quim|quím|product|aditiv|prod[\s._-]?q|vol[\s._-]?q|vol\.?[\s._-]?prod"
        r"|carga|incorpor|ECS\b|ROC\b|AES\b|DEA\b|Sprayberry"
        r"|espaciador|baches", re.I)),
]

DEFAULT_CATEGORY = "Generic/Unknown"


@lru_cache(maxsize=4096)
def categorize(item_name: str | None) -> str:
    """Categorize a single chemical item name. Returns the category string."""
    if not item_name or not item_name.strip():
        return DEFAULT_CATEGORY

    name = item_name.strip()

    # Skip purely numeric or single-character junk entries
    if len(name) <= 2 or name.replace('.', '').replace('-', '').isdigit():
        return DEFAULT_CATEGORY

    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(name):
            return category
    return DEFAULT_CATEGORY


def categorize_batch(item_names: list[str]) -> dict[str, str]:
    """Categorize a list of item names. Returns {item_name: category}."""
    return {name: categorize(name) for name in item_names}
