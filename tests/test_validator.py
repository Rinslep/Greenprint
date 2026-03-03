# tests/test_validator.py
#
# TODO: Tests for pipeline/validator.py.
#
# Test cases to implement:
# - test_validate_simple_valid: validate a decoded simple_valid dict → expect no error, returns model.
# - test_validate_missing_entities_key: pass a dict without 'entities' → expect SchemaError.
# - test_validate_entity_missing_name: entity with no 'name' field → expect SchemaError.
# - test_validate_entity_missing_position: entity with no 'position' → expect SchemaError.
# - test_validate_duplicate_entity_numbers: two entities with the same entity_number
#   → expect SemanticError.
# - test_validate_invalid_connection_reference: connection references an entity_number that
#   doesn't exist → expect SemanticError.
# - test_validate_nan_position: entity with position x=NaN → expect SemanticError.
# - test_validate_item_not_blueprint: blueprint where item != 'blueprint' (and not 'blueprint-book')
#   → expect SchemaError.
#
# All tests load fixtures from tests/fixtures/ or construct minimal dicts inline.
# No network calls permitted.

import pytest
