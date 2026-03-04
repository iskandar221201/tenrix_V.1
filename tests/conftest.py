import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock


@pytest.fixture
def small_df():
    """50 rows, mixed types."""
    np.random.seed(42)
    return pd.DataFrame({
        "id": range(1, 51),
        "amount": np.random.uniform(10, 1000, 50).round(2),
        "quantity": np.random.randint(1, 20, 50),
        "category": np.random.choice(["Electronics", "Clothing", "Food"], 50),
        "region": np.random.choice(["North", "South", "East", "West"], 50),
        "is_returned": np.random.choice([0, 1], 50),
    })


@pytest.fixture
def timeseries_df():
    """200 rows, datetime + numeric."""
    np.random.seed(42)
    base = datetime(2023, 1, 1)
    dates = [base + timedelta(days=i) for i in range(200)]
    return pd.DataFrame({
        "date": dates,
        "sales": np.cumsum(np.random.randn(200) * 10 + 5).round(2),
        "visitors": np.random.randint(50, 500, 200),
        "conversion_rate": np.random.uniform(0.01, 0.15, 200).round(4),
    })


@pytest.fixture
def transactional_df():
    """1000 rows, transaction format."""
    np.random.seed(42)
    items = ["Bread", "Milk", "Eggs", "Butter", "Cheese", "Yogurt", "Juice",
             "Cereal", "Rice", "Pasta", "Sauce", "Oil", "Coffee", "Tea", "Sugar"]
    return pd.DataFrame({
        "transaction_id": np.repeat(range(1, 201), 5),
        "item": np.random.choice(items, 1000),
        "quantity": np.random.randint(1, 5, 1000),
        "price": np.random.uniform(1, 20, 1000).round(2),
    })


@pytest.fixture
def survival_df():
    """100 rows, duration + binary event."""
    np.random.seed(42)
    return pd.DataFrame({
        "patient_id": range(1, 101),
        "duration_months": np.random.exponential(24, 100).round(1),
        "event": np.random.choice([0, 1], 100, p=[0.3, 0.7]),
        "age": np.random.randint(20, 80, 100),
        "treatment": np.random.choice(["A", "B"], 100),
    })


@pytest.fixture
def mock_api_manager():
    """Returns canned JSON responses, never calls real API."""
    manager = MagicMock()
    manager.get_active_provider_name.return_value = "gemini"

    def fake_call(prompt, system=None, *args, **kwargs):
        if "plan" in prompt.lower() or "analyses" in prompt.lower():
            return '''{
                "summary": "Running basic analysis",
                "analyses": [
                    {
                        "analysis_id": "descriptive_stats",
                        "display_name": "Descriptive Statistics",
                        "reason": "Start with basic stats",
                        "params": {},
                        "order": 1
                    }
                ],
                "disclaimer": null
            }'''
        return "Test AI interpretation: The results show significant patterns in the data."

    manager.call.side_effect = fake_call
    manager.validate_current_key.return_value = True
    return manager
