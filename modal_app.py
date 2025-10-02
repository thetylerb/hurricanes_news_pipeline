# modal_app.py
import modal
import subprocess

app = modal.App("canes-news-dashboard")

# Build the image:
# 1) install deps
# 2) copy your code LAST (copy=True so it bakes into the image)
image = (
    modal.Image.debian_slim()
    .pip_install(
        "streamlit",
        "pandas",
        "altair",
        "supabase",
        "python-dotenv",
    )
    .add_local_dir(".", "/app", copy=True)
)

# Serve Streamlit with secrets available
@app.function(
    image=image,
    min_containers=1,  # if your CLI complains, change to keep_warm=1
    secrets=[
        modal.Secret.from_name("supabase"),
        modal.Secret.from_name("openai"),
    ],
)
@modal.web_server(port=8000, startup_timeout=600)
def serve():
    import os, sys
    from pathlib import Path

    script = Path("/app/streamlit_app.py")
    print("Launching Streamlit with:", script, flush=True)
    print("ENV CHECK:",
          "SUPABASE_URL" in os.environ,
          "SUPABASE_ANON_KEY" in os.environ,
          "OPENAI_API_KEY" in os.environ,
          flush=True)

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(script),
        "--server.address", "0.0.0.0",
        "--server.port", "8000",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
    ]
    print("CMD:", " ".join(cmd), flush=True)

    # Non-blocking launch so Modal can finish startup
    subprocess.Popen(cmd, env=os.environ.copy())
    # Do not wait() here—Modal will proxy port 8000 once Streamlit binds
