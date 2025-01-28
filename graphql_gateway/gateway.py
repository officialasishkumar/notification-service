import uvicorn
import jwt
from fastapi import FastAPI, Request, HTTPException
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from typing import Optional

from schema import schema

SECRET_KEY = "MY_SECRET_KEY"
ALGORITHM = "HS256"

app = FastAPI()

graphql_app = GraphQLRouter(schema)

# Middleware to extract and verify JWT, then pass user info to GraphQL context
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
    user_id = None
    if "authorization" in request.headers:
        token = request.headers["authorization"].replace("Bearer ", "")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("userId")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    request.state.userId = user_id

    response = await call_next(request)
    return response

# Custom context for GraphQL to include user_id
def get_context(request: Request) -> dict:
    return {"userId": request.state.userId}

graphql_app = GraphQLRouter(schema, context_getter=get_context)

app.include_router(graphql_app, prefix="/graphql")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
