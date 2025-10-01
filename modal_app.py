from modal import App, Image, Secret, web_server

app = App("canes-news-dashboard")

image = (
    Image.debian_slim()
    .pip_install(
        "streamlit",
        "pandas",
        "altair",
        "supabase",
        "python-dotenv",
    )
    # IMPORTANT: add local files LAST and copy them into the image
    .add_local_dir(".", "/app", copy=True)
)

@app.function(
    image=image,
    secrets=[Secret.from_name("supabase"), Secret.from_name("openai")],
    min_containers=1,
)
@web_server(port=8000, startup_timeout=180)
def serve():
    import os, sys, subprocess
    from pathlib import Path

    script = Path("/app/streamlit_app.py")
    print("Launching Streamlit with script:", script, flush=True)

    # Sanity log: confirm secrets are visible
    print("ENV CHECK:",
          "SUPABASE_URL" in os.environ,
          "SUPABASE_ANON_KEY" in os.environ,
          flush=True)

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(script),
        "--server.address", "0.0.0.0",
        "--server.port", "8000",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]
    print("CMD:", " ".join(cmd), flush=True)

    rc = subprocess.call(cmd, env=env)
    print("Streamlit exited with code:", rc, flush=True)
