"""
__init__.py for models — imports all models so Alembic can discover them.
"""
from app.models.user import User, UserProfile, SpendingProfile, UserGoal  # noqa: F401
from app.models.card import Card  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
