# E-commerce Personalized Notification System

This project implements a microservices-based e-commerce notification system with personalized recommendations, user management, and order tracking capabilities.

## Architecture Overview

The system consists of the following components:

### 1. Services

- **GraphQL Gateway (Port 8000)**
  - Acts as the single entry point for client applications
  - Implements JWT authentication
  - Aggregates data from all microservices
  - Built with FastAPI and Strawberry GraphQL

- **User Service (Port 8001)**
  - Handles user registration and authentication
  - Manages user preferences
  - Issues JWT tokens
  - Uses SQLite database for user data

- **Notification Service (Port 8002)**
  - Stores and manages user notifications
  - Handles marking notifications as read
  - Consumes events from RabbitMQ for new notifications
  - Uses SQLite database for notification storage

- **Recommendation Service (Port 8003)**
  - Generates personalized product recommendations
  - Runs scheduled recommendation tasks
  - Publishes recommendations to notification queue
  - Uses SQLite database for recommendation storage

- **Order Service (Port 8004)**
  - Handles order creation and management
  - Updates order statuses automatically
  - Publishes order events to RabbitMQ
  - Uses SQLite database for order storage

### 2. Message Queues (RabbitMQ)

The following queues are used for asynchronous communication:
- `recommendations_queue`: For new product recommendations
- `order_placed_queue`: For new order events
- `order_updates_queue`: For order status changes

## Setup Instructions

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/officialasishkumar/notification-service.git
cd notification-service
```

2. Start the services:
```bash
docker-compose up --build
```

This will start all services and RabbitMQ. You can view the RabbitMQ management interface at http://localhost:15672 (username: appuser, password: securepassword123)

3. Access the GraphQL Gateway at http://localhost:8000/graphql

### Manual Setup

1. Install Python 3.10 or later

2. Set up RabbitMQ:
```bash
# Install RabbitMQ (Ubuntu/Debian)
sudo apt-get install rabbitmq-server

# Start RabbitMQ
sudo service rabbitmq-server start

# Create user and set permissions
sudo rabbitmqctl add_user appuser securepassword123
sudo rabbitmqctl set_user_tags appuser administrator
sudo rabbitmqctl set_permissions -p / appuser ".*" ".*" ".*"
```

3. Set up each service:

For each service directory (user_service, notification_service, recommendation_service, order_service, graphql_gateway):

```bash
cd <service_directory>
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port <port>
```

Use the following ports:
- GraphQL Gateway: 8000
- User Service: 8001
- Notification Service: 8002
- Recommendation Service: 8003
- Order Service: 8004

## Implementation Details

### Data Flow

1. **User Registration/Login**
   - Client sends request through GraphQL Gateway
   - User Service creates/authenticates user and returns JWT
   - JWT is used for subsequent authenticated requests

2. **Order Placement**
   - Client places order through GraphQL Gateway
   - Order Service creates order and publishes to `order_placed_queue`
   - Recommendation Service consumes order event and generates recommendations
   - Notifications are published to `recommendations_queue`
   - Notification Service consumes and stores notifications

3. **Order Updates**
   - Order Service periodically updates order statuses
   - Updates are published to `order_updates_queue`
   - Notification Service creates notifications for status changes

4. **Recommendations**
   - Generated in two ways:
     a. In response to order events
     b. Through scheduled tasks every 10 minutes
   - Uses mock product data for demonstration
   - Only sent to users who have enabled recommendation preferences

### Authentication Flow

1. Client obtains JWT token through login mutation
2. Token is included in Authorization header: `Bearer <token>`
3. GraphQL Gateway validates token and extracts user ID
4. User ID is passed to resolvers through context

## API Examples & Testing Guide

### GraphQL Queries and Mutations

#### User Management

1. Register User:
```graphql
mutation RegisterUser {
  register(userInput: {
    name: "John Doe"
    email: "john.doe@example.com"
    password: "password123"
    preferences: {
      promotions: true
      orderUpdates: true
      recommendations: true
    }
  }) {
    id
    name
    email
    preferences {
      promotions
      orderUpdates
      recommendations
    }
  }
}
```

2. Login:
```graphql
mutation LoginUser {
  login(loginInput: {
    email: "john.doe@example.com"
    password: "password123"
  }) {
    token
    userId
  }
}
```

**Set Authorization Header**

- In the bottom-left corner of GraphQL Playground, click on **HTTP Headers**.
- Add the following header to authenticate requests:
   ```json
   {
     "Authorization": "Bearer <JWT_TOKEN>"
   }
   ```
   Replace `<JWT_TOKEN>` with the token you received from the login mutation.



3. Get User Details:
```graphql
query GetUserDetails {
  me {
    id
    name
    email
    preferences {
      promotions
      orderUpdates
      recommendations
    }
  }
}
```

4. Update User Preferences:
```graphql
mutation UpdatePreferences {
  updatePreferences(prefsInput: {
    preferences: {
      promotions: false
      orderUpdates: true
      recommendations: true
    }
  }) {
    id
    name
    preferences {
      promotions
      orderUpdates
      recommendations
    }
  }
}
```

#### Order Management

Place 3 Orders:

```graphql
mutation PlaceOrder {
  placeOrder(orderInput: {
    userId: 1
  }) {
    id
    userId
    status
  }
}

mutation PlaceOrder {
  placeOrder(orderInput: {
    userId: 1
  }) {
    id
    userId
    status
  }
}

mutation PlaceOrder {
  placeOrder(orderInput: {
    userId: 1
  }) {
    id
    userId
    status
  }
}
```


#### Notifications and Recommendations

1. Get User Notifications:
```graphql
query GetUnreadNotifications {
  userNotifications {
    id
    userId
    type
    content
    sentAt
    read
  }
}
```

2. Mark Notification as Read:
```graphql
mutation MarkNotificationRead {
  markNotificationRead(notificationId: 1) {
    id
    read
    sentAt
  }
}
```

3. Get User Recommendations:
```graphql
query GetRecommendations {
  recommendations {
    id
    userId
    productId
    reason
  }
}
```

### Testing Workflow

1. **Initial Setup**:
   - Register a new user
   - Login to obtain JWT token
   - Set Authorization header with token

2. **Basic Flow Test**:
   - Place an order
   - Check order status
   - Verify order notifications are received
   - Check recommendations generated from order

3. **Notification Flow Test**:
   - Wait 30 seconds after placing order
   - Check for automated status update notifications
   - Mark notifications as read
   - Verify notification status change

4. **Recommendation Flow Test**:
   - Place multiple orders
   - Wait for scheduled recommendation generation (10 minutes)
   - Check for new personalized recommendations

### Expected Responses

1. Successful Registration:
```json
{
  "data": {
    "register": {
      "id": 1,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "preferences": {
        "promotions": true,
        "orderUpdates": true,
        "recommendations": true
      }
    }
  }
}
```

2. Successful Order Placement:
```json
{
  "data": {
    "placeOrder": {
      "id": 1,
      "userId": 1,
      "status": "placed"
    }
  }
}
```

## Environment Variables

Each service can be configured using environment variables. The following are available:

```bash
# GraphQL Gateway
USER_SERVICE_URL=http://user_service:8001
NOTIF_SERVICE_URL=http://notification_service:8002
RECOMMEND_SERVICE_URL=http://recommendation_service:8003
ORDER_SERVICE_URL=http://order_service:8004
SECRET_KEY=MY_SECRET_KEY
ALGORITHM=HS256

# RabbitMQ (for all services)
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=appuser
RABBITMQ_PASS=securepassword123

# Services
DATABASE_URL=sqlite:///./service_name.db
```

## Database Schema

Each service maintains its own SQLite database:

### User Service
- Table: users
  - id: Integer (Primary Key)
  - name: String
  - email: String (Unique)
  - hashed_password: String
  - preferences: Text (JSON)

### Notification Service
- Table: notifications
  - id: Integer (Primary Key)
  - userId: Integer
  - type: String
  - content: Text
  - sentAt: DateTime
  - read: Boolean

### Recommendation Service
- Table: recommendations
  - id: Integer (Primary Key)
  - userId: Integer
  - productId: Integer
  - reason: String

### Order Service
- Table: orders
  - id: Integer (Primary Key)
  - userId: Integer
  - status: String

## Troubleshooting

1. If services can't connect to RabbitMQ, ensure:
   - RabbitMQ is running and healthy
   - Correct credentials are being used
   - Network connectivity between containers/services exists

2. If databases aren't working:
   - Check if SQLite files are created
   - Ensure write permissions in service directories

3. If JWT authentication fails:
   - Verify SECRET_KEY matches between services
   - Check token expiration
   - Ensure token is properly formatted in Authorization header