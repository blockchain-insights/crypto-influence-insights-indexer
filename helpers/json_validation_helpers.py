import json
from jsonschema import validate, ValidationError
from loguru import logger

def validate_json_dataset(file_content: str, schema_path: str) -> bool:
    """
    Validates a JSON dataset using a specified schema.

    Args:
        file_content (str): The JSON content as a string.
        schema_path (str): Path to the JSON schema file.

    Returns:
        bool: True if the dataset is valid, False otherwise.
    """
    try:
        # Load schema
        with open(schema_path, "r") as schema_file:
            schema = json.load(schema_file)

        # Parse JSON content
        dataset = json.loads(file_content)

        # Validate JSON against schema
        validate(instance=dataset, schema=schema)
        logger.info("Dataset is valid.")
        return True
    except ValidationError as e:
        logger.error(f"Dataset validation error: {e.message} at {list(e.path)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return False
