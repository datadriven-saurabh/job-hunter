"""Locks shared by mutations in this single-process local app."""
from threading import RLock

queue_reservation = RLock()
profile_write = RLock()
