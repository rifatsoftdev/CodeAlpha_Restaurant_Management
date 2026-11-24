"""Load sample data:  python -m app.seed"""
from app.models import models
from app.core.database import Base, SessionLocal, engine


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(models.MenuItem).first():
        print("Database already has data - skipping seed.")
        return

    flour = models.InventoryItem(name="Flour", unit="kg", quantity=20, reorder_level=5)
    cheese = models.InventoryItem(name="Cheese", unit="kg", quantity=10, reorder_level=3)
    tomato = models.InventoryItem(name="Tomato", unit="kg", quantity=15, reorder_level=4)
    db.add_all([flour, cheese, tomato])
    db.flush()

    pizza = models.MenuItem(name="Margherita Pizza", price=9.5, category="main", description="Tomato, mozzarella, basil")
    pizza.recipe = [
        models.RecipeIngredient(inventory_item_id=flour.id, quantity_required=0.25),
        models.RecipeIngredient(inventory_item_id=cheese.id, quantity_required=0.15),
        models.RecipeIngredient(inventory_item_id=tomato.id, quantity_required=0.10),
    ]
    salad = models.MenuItem(name="Tomato Salad", price=5.0, category="starter")
    salad.recipe = [models.RecipeIngredient(inventory_item_id=tomato.id, quantity_required=0.20)]
    db.add_all([pizza, salad])

    db.add_all([models.Table(number=n, capacity=c) for n, c in [(1, 2), (2, 2), (3, 4), (4, 6)]])
    db.commit()
    print("Seeded sample menu, inventory and tables.")


if __name__ == "__main__":
    run()
