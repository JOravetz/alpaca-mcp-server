"""WebSocket handlers for real-time communication."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

from ...utils.timezone_utils import get_eastern_time_string


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        self.logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSockets"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected WebSockets"""
        message = json.dumps(data)
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint handler"""
    await websocket_manager.connect(websocket)

    try:
        # Send initial status
        initial_status = {
            "type": "connection_established",
            "timestamp": get_eastern_time_string(),
            "message": "WebSocket connection established",
        }
        await websocket_manager.send_personal_message(json.dumps(initial_status), websocket)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for incoming messages
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                if message_data.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": get_eastern_time_string()}),
                        websocket,
                    )
                elif message_data.get("type") == "subscribe":
                    # Handle subscription requests
                    await websocket_manager.send_personal_message(
                        json.dumps(
                            {
                                "type": "subscription_ack",
                                "subscribed_to": message_data.get("topics", []),
                                "timestamp": get_eastern_time_string(),
                            }
                        ),
                        websocket,
                    )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON received
                error_msg = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": get_eastern_time_string(),
                }
                await websocket_manager.send_personal_message(json.dumps(error_msg), websocket)
            except Exception as e:
                # Other errors
                error_msg = {
                    "type": "error",
                    "message": f"Error processing message: {str(e)}",
                    "timestamp": get_eastern_time_string(),
                }
                await websocket_manager.send_personal_message(json.dumps(error_msg), websocket)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


async def broadcast_status_update(status_data: dict):
    """Broadcast status updates to all connected clients"""
    message = {
        "type": "status_update",
        "timestamp": get_eastern_time_string(),
        "data": status_data,
    }
    await websocket_manager.broadcast_json(message)


async def broadcast_signal_update(signal_data: dict):
    """Broadcast signal updates to all connected clients"""
    message = {
        "type": "signal_update",
        "timestamp": get_eastern_time_string(),
        "data": signal_data,
    }
    await websocket_manager.broadcast_json(message)


async def broadcast_position_update(position_data: dict):
    """Broadcast position updates to all connected clients"""
    message = {
        "type": "position_update",
        "timestamp": get_eastern_time_string(),
        "data": position_data,
    }
    await websocket_manager.broadcast_json(message)


async def broadcast_alert(alert_data: dict):
    """Broadcast alerts to all connected clients"""
    message = {"type": "alert", "timestamp": get_eastern_time_string(), "data": alert_data}
    await websocket_manager.broadcast_json(message)
