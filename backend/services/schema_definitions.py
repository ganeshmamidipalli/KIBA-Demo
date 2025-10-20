"""
JSON schema definitions for KPA One-Flow API responses.
"""

INTAKE_SCHEMA = {
    "name": "ProcurementIntake",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["questions", "ready"]},
            "requirements_summary": {"type": "string"},
            "missing_info_questions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 6
            }
        },
        "required": ["status", "requirements_summary", "missing_info_questions"]
    },
    "strict": True
}

SEARCH_READY_RECS_SCHEMA = {
    "name": "ProcurementSearchReadyRecs",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string"},
            "summary": {"type": "string"},
            "recommendations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "specs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1
                        },
                        "estimated_price_usd": {
                            "anyOf": [{"type": "number"}, {"type": "null"}]
                        },
                        "meets_budget": {"type": "boolean"},
                        "value_note": {"type": "string"},
                        "rationale": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 100},
                        "vendor_search": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "model_name": {"type": "string"},
                                "spec_fragments": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                    "maxItems": 3
                                },
                                "region_hint": {
                                    "anyOf": [{"type": "string"}, {"type": "null"}]
                                },
                                "budget_hint_usd": {
                                    "anyOf": [{"type": "number"}, {"type": "null"}]
                                },
                                "query_seed": {"type": "string"}
                            },
                            "required": [
                                "model_name",
                                "spec_fragments", 
                                "region_hint",
                                "budget_hint_usd",
                                "query_seed"
                            ]
                        }
                    },
                    "required": [
                        "id",
                        "name",
                        "specs",
                        "estimated_price_usd",
                        "meets_budget",
                        "value_note",
                        "rationale",
                        "score",
                        "vendor_search"
                    ]
                }
            },
            "recommended_index": {"type": "integer", "minimum": 0},
            "selection_mode": {"type": "string"},
            "disclaimer": {"type": "string"}
        },
        "required": [
            "schema_version",
            "summary",
            "recommendations",
            "recommended_index",
            "selection_mode",
            "disclaimer"
        ]
    },
    "strict": True
}
