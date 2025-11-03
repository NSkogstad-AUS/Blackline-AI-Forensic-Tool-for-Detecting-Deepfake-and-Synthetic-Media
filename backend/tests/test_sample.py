from fastapi import FastAPI


def test_import_api_and_health_route_exists():
    """Smoke test: import the FastAPI app and assert the health route is registered.

    This is a lightweight check that the application imports cleanly and exposes
    the `/api/health` endpoint used by the front-end and other tests.
    """
    from backend.src import api_server

    app = getattr(api_server, "app", None)
    assert isinstance(app, FastAPI)

    # Ensure /api/health exists in the routes
    paths = {r.path for r in app.routes}
    assert "/api/health" in paths or any(p.path == "/api/health" for p in app.routes)
