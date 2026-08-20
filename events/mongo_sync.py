"""
MongoDB sync layer for Event Management ERP.

This module provides:
  - A lazy-initialised MongoDB client (no crash when MongoDB is unavailable).
  - Helper functions to upsert/delete Event and Category documents.
  - Django signal receivers that automatically mirror SQLite → MongoDB
    whenever an Event or Category is saved or deleted.

Configuration (settings.py):
    MONGODB_URI  = "mongodb://localhost:27017/"   # or Atlas URI
    MONGODB_DB   = "event_management"
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# ─── lazy client ─────────────────────────────────────────────────────────────
_client = None
_db = None


def _get_db():
    """Return the MongoDB database handle, initialising the client on first call.
    Returns None (silently) when pymongo is not installed or MongoDB is unreachable.
    """
    global _client, _db
    if _db is not None:
        return _db
    try:
        from pymongo import MongoClient  # type: ignore
        uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017/')
        db_name = getattr(settings, 'MONGODB_DB', 'event_management')
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        # Force a connection check
        _client.admin.command('ping')
        _db = _client[db_name]
        logger.info("MongoDB connected: %s / %s", uri, db_name)
        return _db
    except Exception as exc:
        logger.warning("MongoDB unavailable — sync disabled: %s", exc)
        return None


def _collection(name: str):
    db = _get_db()
    if db is None:
        return None
    return db[name]


# ─── serialisers ─────────────────────────────────────────────────────────────

def _serialise_category(instance) -> dict[str, Any]:
    return {
        '_id': instance.pk,
        'name': instance.name,
        'code': instance.code,
        'image': instance.image.url if instance.image else None,
        'priority': instance.priority,
        'status': instance.status,
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
    }


def _serialise_event(instance) -> dict[str, Any]:
    return {
        '_id': instance.pk,
        'uid': instance.uid,
        'title': instance.title,
        'category_id': instance.category_id,
        'category_name': instance.category.name if instance.category else None,
        'description': instance.description,
        'session_name': instance.session_name,
        'speaker_name': instance.speaker_name,
        'start_time': instance.start_time.isoformat() if instance.start_time else None,
        'end_time': instance.end_time.isoformat() if instance.end_time else None,
        'venue_name': instance.venue_name,
        'location': instance.location,
        'price': float(instance.price),
        'total_budget': float(instance.total_budget),
        'max_attendance': instance.max_attendance,
        'event_type': instance.event_type,
        'subcategory': instance.subcategory,
        'job_category': instance.job_category,
        'status': instance.status,
        'created_by_id': instance.created_by_id,
        'created_by': (
            instance.created_by.get_full_name() or instance.created_by.username
            if instance.created_by else None
        ),
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
    }


# ─── upsert / delete helpers ─────────────────────────────────────────────────

def sync_category(instance):
    col = _collection('categories')
    if col is None:
        return
    try:
        doc = _serialise_category(instance)
        col.replace_one({'_id': doc['_id']}, doc, upsert=True)
        logger.debug("MongoDB: upserted category %s", instance.pk)
    except Exception as exc:
        logger.error("MongoDB: failed to sync category %s: %s", instance.pk, exc)


def delete_category(instance):
    col = _collection('categories')
    if col is None:
        return
    try:
        col.delete_one({'_id': instance.pk})
        logger.debug("MongoDB: deleted category %s", instance.pk)
    except Exception as exc:
        logger.error("MongoDB: failed to delete category %s: %s", instance.pk, exc)


def sync_event(instance):
    col = _collection('events')
    if col is None:
        return
    try:
        doc = _serialise_event(instance)
        col.replace_one({'_id': doc['_id']}, doc, upsert=True)
        logger.debug("MongoDB: upserted event %s", instance.pk)
    except Exception as exc:
        logger.error("MongoDB: failed to sync event %s: %s", instance.pk, exc)


def delete_event(instance):
    col = _collection('events')
    if col is None:
        return
    try:
        col.delete_one({'_id': instance.pk})
        logger.debug("MongoDB: deleted event %s", instance.pk)
    except Exception as exc:
        logger.error("MongoDB: failed to delete event %s: %s", instance.pk, exc)


# ─── signal receivers ────────────────────────────────────────────────────────

def _connect_signals():
    """Import models here to avoid circular imports; called from AppConfig.ready()."""
    from .models import Category, Event  # noqa: PLC0415

    @receiver(post_save, sender=Category, dispatch_uid='mongo_sync_category_save')
    def _on_category_save(sender, instance, **kwargs):
        sync_category(instance)

    @receiver(post_delete, sender=Category, dispatch_uid='mongo_sync_category_delete')
    def _on_category_delete(sender, instance, **kwargs):
        delete_category(instance)

    @receiver(post_save, sender=Event, dispatch_uid='mongo_sync_event_save')
    def _on_event_save(sender, instance, **kwargs):
        sync_event(instance)

    @receiver(post_delete, sender=Event, dispatch_uid='mongo_sync_event_delete')
    def _on_event_delete(sender, instance, **kwargs):
        delete_event(instance)
