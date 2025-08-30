from typing import Sequence, Mapping
import re
from loguru import logger
from app.ynab_client import Category


def select_categories(
    all_categories: list[Category],
    categories_to_select: dict[str, list[str]],
) -> list[Category]:
    if not categories_to_select:
        return []

    groups: dict[str, list[Category]] = {}
    for c in all_categories:
        groups.setdefault(c.group_name, []).append(c)

    selected: dict[str, Category] = {}

    for group_name, cat_names in categories_to_select.items():
        group_cats = groups.get(group_name, [])
        if not group_cats:
            logger.warning(f"No matching category group for '{group_name}'")
            continue

        if not cat_names or (len(cat_names) == 1 and cat_names[0] == "*"):
            for c in group_cats:
                selected[c.id] = c
            continue

        for cat_name in cat_names:
            matches = [c for c in group_cats if c.name == cat_name]
            if not matches:
                logger.warning(
                    f"No matching category '{cat_name}' in group '{group_name}'"
                )
                continue
            for c in matches:
                selected[c.id] = c

    return list(selected.values())
