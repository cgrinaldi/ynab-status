from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
import ynab


class Budget(BaseModel):
    id: str
    name: str
    last_modified_on: Optional[datetime]


class Category(BaseModel):
    id: str
    name: str
    group_id: str
    group_name: str
    hidden: bool
    deleted: bool
    budgeted_mu: int = 0
    activity_mu: int = 0
    available_mu: int = 0


class CategoryGroup(BaseModel):
    id: str
    name: str
    hidden: bool
    deleted: bool
    categories: list[Category] = []


def _as_aware_dt(v: Optional[str | datetime]) -> Optional[datetime]:
    """Return a timezone-aware datetime or None, accepting str or datetime."""
    if isinstance(v, datetime):
        # ensure tz-aware (YNAB values should be UTC)
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        s = v.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return None


@dataclass
class YnabSDKClient:
    token: str
    timeout_seconds: float = 10.0

    def __post_init__(self):
        if not self.token:
            raise RuntimeError("Missing YNAB token. Set YNAB_TOKEN in .env")

        self._config = ynab.Configuration(access_token=self.token)
        self._api_client: Optional[ynab.ApiClient] = None
        self.budgets_api: Optional[ynab.BudgetsApi] = None
        self.categories_api: Optional[ynab.CategoriesApi] = None

    # this code is run at the beginning of a context manager (e.g., with ...)
    def __enter__(self) -> YnabSDKClient:
        self._api_client = ynab.ApiClient(self._config)
        try:
            self._api_client.rest_client.pool_manager.connection_pool_kw["timeout"] = (
                self.timeout_seconds
            )
        except Exception:
            pass

        self.budgets_api = ynab.BudgetsApi(self._api_client)
        self.categories_api = ynab.CategoriesApi(self._api_client)
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if self._api_client:
            self._api_client.__exit__(exc_type, exc_val, tb)

    def get_budgets(self) -> list[Budget]:
        assert self.budgets_api is not None
        resp = self.budgets_api.get_budgets()
        budgets: list[Budget] = []
        for b in resp.data.budgets:
            budgets.append(
                Budget(
                    id=b.id,
                    name=b.name,
                    last_modified_on=_as_aware_dt(b.last_modified_on),
                )
            )
        return budgets

    def get_budget_by_name(self, budget_name: str) -> Budget:
        for b in self.get_budgets():
            if b.name == budget_name:
                return b
        raise ValueError(f"Budget not found by name: {budget_name}")

    def get_category_groups(
        self, budget_id: str, include_hidden: bool = False
    ) -> list[CategoryGroup]:
        assert self.categories_api is not None, "Use YnabSDKClient as a context manager"
        resp = self.categories_api.get_categories(budget_id)
        groups: list[CategoryGroup] = []
        for grp in resp.data.category_groups:
            group_hidden = bool(getattr(grp, "hidden", False))
            group_deleted = bool(getattr(grp, "deleted", False))
            if not include_hidden and (group_hidden or group_deleted):
                continue
            cats: list[Category] = []
            for c in grp.categories:
                cat_hidden = bool(getattr(c, "hidden", False))
                cat_deleted = bool(getattr(c, "deleted", False))
                if not include_hidden and (cat_hidden or cat_deleted):
                    continue
                cats.append(
                    Category(
                        id=c.id,
                        name=c.name,
                        group_id=grp.id,
                        group_name=grp.name,
                        hidden=cat_hidden,
                        deleted=cat_deleted,
                        budgeted_mu=int(getattr(c, "budgeted", 0)),
                        activity_mu=int(getattr(c, "activity", 0)),
                        available_mu=int(getattr(c, "balance", 0)),
                    )
                )
            groups.append(
                CategoryGroup(
                    id=grp.id,
                    name=grp.name,
                    hidden=group_hidden,
                    deleted=group_deleted,
                    categories=cats,
                )
            )
        return groups

    def get_categories(
        self, budget_id: str, include_hidden: bool = False
    ) -> list[Category]:
        """Return all categories for a budget, optionally including hidden/deleted.

        This reuses `get_category_groups` and flattens the categories.
        """
        groups = self.get_category_groups(budget_id, include_hidden=include_hidden)
        categories: list[Category] = []
        for g in groups:
            categories.extend(g.categories)
        return categories

    def find_category_by_group_and_name(
        self,
        budget_id: str,
        group_name: str,
        category_name: str,
        include_hidden: bool = False,
    ) -> Category:
        groups = self.get_category_groups(budget_id, include_hidden=include_hidden)
        gmatch = next(
            (g for g in groups if g.name.strip().lower() == group_name.strip().lower()),
            None,
        )
        if not gmatch:
            raise ValueError(f"Category group not found: {group_name}")
        cmatch = next(
            (
                c
                for c in gmatch.categories
                if c.name.strip().lower() == category_name.strip().lower()
            ),
            None,
        )
        if not cmatch:
            raise ValueError(
                f"Category not found in group '{group_name}': {category_name}"
            )
        return cmatch
