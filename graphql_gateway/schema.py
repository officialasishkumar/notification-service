# graphql_gateway/schema.py

import os
import strawberry
from typing import List, Optional, Dict
import requests
from strawberry.types import Info
from fastapi.encoders import jsonable_encoder
import json

SECRET_KEY = os.getenv("SECRET_KEY", "MY_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")
NOTIF_SERVICE_URL = os.getenv("NOTIF_SERVICE_URL", "http://notification_service:8002")
RECOMMEND_SERVICE_URL = os.getenv("RECOMMEND_SERVICE_URL", "http://recommendation_service:8003")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8004")

@strawberry.type
class PreferencesType:
    promotions: bool
    orderUpdates: bool
    recommendations: bool

@strawberry.type
class NotificationType:
    id: int
    userId: int
    type: str
    content: str
    sentAt: str
    read: bool

@strawberry.type
class RecommendationType:
    id: int
    userId: int
    productId: int
    reason: Optional[str]

@strawberry.type
class OrderType:
    id: int
    userId: int
    status: str

@strawberry.type
class UserType:
    id: int
    name: str
    email: str
    preferences: PreferencesType

@strawberry.type
class AuthPayload:
    token: str
    userId: int  # Changed from user_id to userId

# Input Types
@strawberry.input
class PreferencesInput:
    promotions: bool = False
    orderUpdates: bool = False
    recommendations: bool = False

@strawberry.input
class UserRegisterInput:
    name: str
    email: str
    password: str
    preferences: Optional[PreferencesInput] = strawberry.field(default_factory=lambda: PreferencesInput())

@strawberry.input
class UserLoginInput:
    email: str
    password: str

@strawberry.input
class UpdatePreferencesInput:
    preferences: PreferencesInput

@strawberry.input
class PlaceOrderInput:
    userId: int  # Changed from user_id to userId

# Queries
@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> Optional[UserType]:
        user_id = info.context.get("userId")
        if not user_id:
            raise Exception("Not authenticated")
        response = requests.get(f"{USER_SERVICE_URL}/user/{user_id}")
        if response.status_code == 200:
            user_data = response.json()
            preferences = json.loads(user_data["preferences"])
            preferences_obj = PreferencesType(**preferences)
            return UserType(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                preferences=preferences_obj
            )
        elif response.status_code == 404:
            raise Exception("User not found")
        else:
            raise Exception(f"Failed to fetch user details: {response.text}")

    @strawberry.field
    def userNotifications(self, info: Info) -> List[NotificationType]:
        user_id = info.context.get("userId")  # Changed from user_id to userId
        if not user_id:
            return []
        response = requests.get(f"{NOTIF_SERVICE_URL}/notifications/unread/{user_id}")
        if response.status_code == 200:
            notifs = response.json()
            return [NotificationType(**n) for n in notifs]
        return []

    @strawberry.field
    def recommendations(self, info: Info) -> List[RecommendationType]:
        user_id = info.context.get("userId")  # Changed from user_id to uerId
        if not user_id:
            return ["Im dumb"]
        response = requests.get(f"{RECOMMEND_SERVICE_URL}/recommendations/{user_id}")
        if response.status_code == 200:
            recs = response.json()
            return [RecommendationType(**r) for r in recs]
        return []

    @strawberry.field
    def orders(self, info: Info) -> List[OrderType]:
        user_id = info.context.get("userId")  # Changed from user_id to userId
        if not user_id:
            return []
        response = requests.get(f"{ORDER_SERVICE_URL}/orders/{user_id}")
        if response.status_code == 200:
            orders = response.json()
            return [OrderType(**o) for o in orders]
        return []

# Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, user_input: UserRegisterInput) -> UserType:
        # Serialize the user_input using jsonable_encoder
        payload = jsonable_encoder(user_input)
        response = requests.post(f"{USER_SERVICE_URL}/register", json=payload)
        if response.status_code == 200:
            user_data = response.json()
            preferences = json.loads(user_data["preferences"])
            preferences_obj = PreferencesType(**preferences)
            return UserType(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                preferences=preferences_obj
            )
        elif response.status_code == 400:
            error = response.json().get("message", "Failed to register user")
            raise Exception(error)
        else:
            raise Exception(f"Failed to register user: {response.text}")

    @strawberry.mutation
    def login(self, login_input: UserLoginInput) -> AuthPayload:
        response = requests.post(f"{USER_SERVICE_URL}/login", json=login_input.__dict__)
        if response.status_code == 200:
            data = response.json()
            return AuthPayload(token=data["token"], userId=data["userId"])  # Changed from user_id to userId
        else:
            error = response.json().get("message", "Login failed")
            raise Exception(error)

    @strawberry.mutation
    def updatePreferences(self, prefs_input: UpdatePreferencesInput, info: Info) -> UserType:
        user_id = info.context.get("userId")  # Changed from user_id to userId
        if not user_id:
            raise Exception("Not authenticated")
        response = requests.put(
            f"{USER_SERVICE_URL}/user/{user_id}/preferences",
            json=jsonable_encoder(prefs_input)
        )
        if response.status_code == 200:
            # Fetch updated user details
            user_response = requests.get(f"{USER_SERVICE_URL}/user/{user_id}")
            if user_response.status_code == 200:
                user_data = user_response.json()
                preferences = json.loads(user_data["preferences"])
                preferences_obj = PreferencesType(**preferences)
                return UserType(
                    id=user_data["id"],
                    name=user_data["name"],
                    email=user_data["email"],
                    preferences=preferences_obj
                )
            else:
                raise Exception("Failed to fetch user after updating preferences")
        else:
            error = response.json().get("message", "Failed to update preferences")
            raise Exception(error)

    @strawberry.mutation
    def placeOrder(self, order_input: PlaceOrderInput) -> OrderType:
        response = requests.post(
            f"{ORDER_SERVICE_URL}/order",
            json={"userId": order_input.userId}  # Changed from user_id to userId
        )
        if response.status_code == 200:
            return OrderType(**response.json())
        else:
            raise Exception(f"Failed to place order: {response.text}")

    @strawberry.mutation
    def markNotificationRead(self, notification_id: int, info: Info) -> bool:
        user_id = info.context.get("userId")  # Changed from user_id to userId
        if not user_id:
            raise Exception("Not authenticated")
        response = requests.post(f"{NOTIF_SERVICE_URL}/notifications/mark-read/{notification_id}")
        if response.status_code == 200:
            return True
        else:
            raise Exception(f"Failed to mark notification as read: {response.text}")

schema = strawberry.Schema(query=Query, mutation=Mutation)
