swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "frontend_apispec",
            "route": "/api-docs/frontend/apispec.json",
            "title": "Frontend API",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        },
        {
            "endpoint": "inter_service_apispec",
            "route": "/api-docs/inter-service/apispec.json",
            "title": "Inter-Service API",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        },
        {
            "endpoint": "combined_apispec",
            "route": "/api-docs/combined/apispec.json",
            "title": "Combined API",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        },
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api-docs/",
}

swagger_template = {
    "info": {
        "title": "Trip & Fare Core Service API",
        "version": "1.0.0",
        "description": "API documentation for the Rideshare Trip & Fare Core Service",
    },
    "tags": [
        {"name": "Trips", "description": "Trip management endpoints for frontend applications"},
        {"name": "Driver Actions", "description": "Driver-specific trip actions"},
        {"name": "Driver Dashboard", "description": "Driver dashboard and earnings endpoints"},
        {"name": "Rider Dashboard", "description": "Rider trip history and statistics"},
        {"name": "Fares", "description": "Fare calculation and configuration"},
        {"name": "Analytics", "description": "Trip analytics and reporting"},
        {"name": "Health", "description": "Service health and status endpoints"},
        {"name": "Internal", "description": "Internal service endpoints"},
    ],
}
