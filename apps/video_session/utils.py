import base64
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ZOOM_REQUEST_TIMEOUT = 10  # seconds


def get_zoom_access_token():
    """Generates (or returns a cached) Server-to-Server OAuth access token from Zoom."""
    cached_token = cache.get("zoom_access_token")
    if cached_token:
        return cached_token

    client_id = settings.ZOOM_CLIENT_ID
    client_secret = settings.ZOOM_CLIENT_SECRET
    account_id = settings.ZOOM_ACCOUNT_ID

    auth_string = f"{client_id}:{client_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    url = "https://zoom.us/oauth/token"
    params = {
        "grant_type": "account_credentials",
        "account_id": account_id,
    }
    headers = {
        "Authorization": f"Basic {encoded_auth}"
    }

    try:
        response = requests.post(
            url, headers=headers, params=params, timeout=ZOOM_REQUEST_TIMEOUT
        )
    except requests.RequestException as e:
        logger.error("Zoom token request failed: %s", e)
        return None

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        # Cache slightly under actual expiry to avoid using a stale token
        cache.set("zoom_access_token", token, timeout=max(expires_in - 60, 60))
        return token

    logger.error(
        "Zoom Token Error: %s - %s", response.status_code, response.text
    )
    return None


def create_zoom_meeting(topic, start_time, duration_minutes=30, user_id="me"):
    """Creates a scheduled Zoom meeting and returns join/start URLs."""
    token = get_zoom_access_token()
    if not token:
        return None

    url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "topic": topic,
        "type": 2,
        "start_time": start_time,
        "duration": duration_minutes,
        "timezone": "UTC",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "waiting_room": True,
        },
    }

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=ZOOM_REQUEST_TIMEOUT
        )
    except requests.RequestException as e:
        logger.error("Zoom meeting creation request failed: %s", e)
        return None

    if response.status_code == 201:
        data = response.json()
        return {
            "meeting_id": data.get("id"),
            "join_url": data.get("join_url"),
            "start_url": data.get("start_url"),
        }

    logger.error(
        "Zoom Meeting Error: %s - %s", response.status_code, response.text
    )
    return None


def get_zoom_meeting_details(meeting_id):
    """Fetches meeting details from Zoom API by meeting ID."""
    if not meeting_id:
        return None

    token = get_zoom_access_token()
    if not token:
        return None

    url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=ZOOM_REQUEST_TIMEOUT)
    except requests.RequestException as e:
        logger.error("Zoom meeting details request failed: %s", e)
        return None

    if response.status_code == 200:
        data = response.json()
        return {
            "meeting_id": data.get("id"),
            "join_url": data.get("join_url"),
            "start_time": data.get("start_time"),
        }

    logger.error(
        "Zoom Meeting Details Error: %s - %s", response.status_code, response.text
    )
    return None