from app.config import load_secrets
from app.helpers import mu_to_decimal
from app.ynab_client import YnabSDKClient


if __name__ == "__main__":
    secrets = load_secrets()
    with YnabSDKClient(secrets.YNAB_API_KEY) as ynab_client:
        budget = ynab_client.get_budget_by_name("Back in SF")
        print(f"Budget: {budget.name}")

        category = ynab_client.find_category_by_group_and_name(
            budget.id, "Household Expenses", "Groceries"
        )
        import pdb

        pdb.set_trace()
