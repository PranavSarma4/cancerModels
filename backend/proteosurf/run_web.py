"""Entry point for the FastAPI web server."""

import uvicorn


def main():
    uvicorn.run(
        "proteosurf.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
