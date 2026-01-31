"""DynamoDB client for Second Brain data operations."""

import os
from typing import Type, TypeVar, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class DynamoDBClient:
    """Simple DynamoDB client for CRUD operations with Pydantic models."""

    def __init__(self):
        """Initialize DynamoDB client."""
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "second-brain")
        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Initialize DynamoDB resource
        dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = dynamodb.Table(self.table_name)

    def put_item(self, model: BaseModel) -> None:
        """
        Save a Pydantic model to DynamoDB.

        Args:
            model: Pydantic model with to_dynamo() method

        Raises:
            AttributeError: If model doesn't have to_dynamo() method
        """
        if not hasattr(model, "to_dynamo"):
            raise AttributeError(
                f"Model {type(model).__name__} must have to_dynamo() method"
            )

        item = model.to_dynamo()
        self.table.put_item(Item=item)

    def get_item(self, pk: str, sk: str, model_class: Type[T]) -> Optional[T]:
        """
        Get an item from DynamoDB and convert to model.

        Args:
            pk: Partition key value
            sk: Sort key value
            model_class: Pydantic model class to deserialize into

        Returns:
            Model instance or None if not found

        Raises:
            AttributeError: If model doesn't have from_dynamo() method
        """
        if not hasattr(model_class, "from_dynamo"):
            raise AttributeError(
                f"Model {model_class.__name__} must have from_dynamo() classmethod"
            )

        response = self.table.get_item(Key={"PK": pk, "SK": sk})

        if "Item" not in response:
            return None

        return model_class.from_dynamo(response["Item"])

    def query_by_pk(self, pk: str, model_class: Type[T]) -> List[T]:
        """
        Query items by partition key and convert to models.

        Args:
            pk: Partition key value
            model_class: Pydantic model class to deserialize into

        Returns:
            List of model instances

        Raises:
            AttributeError: If model doesn't have from_dynamo() method
        """
        if not hasattr(model_class, "from_dynamo"):
            raise AttributeError(
                f"Model {model_class.__name__} must have from_dynamo() classmethod"
            )

        response = self.table.query(KeyConditionExpression=Key("PK").eq(pk))

        return [model_class.from_dynamo(item) for item in response.get("Items", [])]

    def query_by_pk_and_sk_prefix(
        self, pk: str, sk_prefix: str, model_class: Type[T]
    ) -> List[T]:
        """
        Query items by partition key and sort key prefix.

        Useful for querying all items of a specific type, e.g.,
        all tasks for a user: pk="user#123", sk_prefix="task#"

        Args:
            pk: Partition key value
            sk_prefix: Sort key prefix to match (e.g., "task#")
            model_class: Pydantic model class to deserialize into

        Returns:
            List of model instances

        Raises:
            AttributeError: If model doesn't have from_dynamo() method
        """
        if not hasattr(model_class, "from_dynamo"):
            raise AttributeError(
                f"Model {model_class.__name__} must have from_dynamo() classmethod"
            )

        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix)
        )

        return [model_class.from_dynamo(item) for item in response.get("Items", [])]

    def update_item(self, pk: str, sk: str, updates: dict) -> None:
        """
        Update specific attributes of an item.

        Args:
            pk: Partition key value
            sk: Sort key value
            updates: Dictionary of attribute names and values to update

        Example:
            client.update_item(
                "user#123",
                "task#abc",
                {"status": "completed", "completed_at": datetime.utcnow().isoformat()}
            )
        """
        if not updates:
            return

        # Build update expression
        update_expr_parts = []
        expr_values = {}

        for key, value in updates.items():
            update_expr_parts.append(f"{key} = :{key}")
            expr_values[f":{key}"] = value

        update_expr = "SET " + ", ".join(update_expr_parts)

        self.table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
        )

    def delete_item(self, pk: str, sk: str) -> None:
        """
        Delete an item from DynamoDB.

        Args:
            pk: Partition key value
            sk: Sort key value
        """
        self.table.delete_item(Key={"PK": pk, "SK": sk})

    def batch_write(self, models: List[BaseModel]) -> None:
        """
        Batch write multiple items to DynamoDB.

        More efficient than individual put_item calls.

        Args:
            models: List of Pydantic models with to_dynamo() method
        """
        if not models:
            return

        with self.table.batch_writer(batch_size=25) as batch:
            for model in models:
                if not hasattr(model, "to_dynamo"):
                    raise AttributeError(
                        f"Model {type(model).__name__} must have to_dynamo() method"
                    )
                batch.put_item(Item=model.to_dynamo())

    def scan_by_type(self, user_id: str, item_type: str, model_class: Type[T]) -> List[T]:
        """
        Scan all items of a specific type for a user.

        Less efficient than query but works with GSI on type field.

        Args:
            user_id: User ID
            item_type: Type filter (e.g., "task", "todo", "reminder")
            model_class: Pydantic model class to deserialize into

        Returns:
            List of model instances
        """
        if not hasattr(model_class, "from_dynamo"):
            raise AttributeError(
                f"Model {model_class.__name__} must have from_dynamo() classmethod"
            )

        # First query by PK to get items for this user
        response = self.table.query(KeyConditionExpression=Key("PK").eq(f"user#{user_id}"))

        # Filter by type in Python (could use GSI for better performance)
        items = [
            model_class.from_dynamo(item)
            for item in response.get("Items", [])
            if item.get("type") == item_type
        ]

        return items
