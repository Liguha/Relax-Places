__all__ = ["should_recalculate"]

def should_recalculate(n_unprocessed: int, n_total: int) -> bool:
    return (n_total - n_unprocessed) > 0    # just test placeholder