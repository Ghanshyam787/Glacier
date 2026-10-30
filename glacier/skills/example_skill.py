"""Example Glacier skill - copy karke apna banao. File ka naam '_' se shuru ho to load nahi hoti."""

from registry import tool


@tool(category="custom", label="Coin flip")
def coin_flip() -> str:
    """Flip a coin and return heads or tails."""
    import random
    return random.choice(["Heads", "Tails"])
