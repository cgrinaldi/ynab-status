from app.config import load_secrets
from app.helpers import mu_to_decimal
from app.ynab_client import YnabSDKClient
from app.domain import select_categories


if __name__ == "__main__":
    secrets = load_secrets()
    with YnabSDKClient(secrets.YNAB_API_KEY) as ynab_client:
        budget = ynab_client.get_budget_by_name("Back in SF")
        print(f"Budget: {budget.name}")

        categories = ynab_client.get_categories(budget.id)
        selected_cats = select_categories(
            categories, {"Household Expenses": ["Groceries", "Misc"]}
        )
        import pdb

        pdb.set_trace()
