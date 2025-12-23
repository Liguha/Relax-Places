__all__ = ["should_recalculate"]

def should_recalculate(n_unprocessed: int, n_total: int) -> bool:
    
    if n_total == 0:
        return False
    return n_unprocessed >= 0.1 * n_total