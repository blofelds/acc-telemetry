# Deployment Guide: Hugging Face Spaces

## Backend Deployment

1. **Create a New Space**:
   - Go to [huggingface.co/spaces](https://huggingface.co/spaces).
   - Click **"Create new Space"**.
   - **Name**: `acc-telemetry-backend` (or similar).
   - **License**: MIT (or your choice).
   - **SDK**: Select **Docker**.
   - **Hardware**: Select **Free** (2 vCPU, 16GB RAM).
   - Click **"Create Space"**.

2. **Push Code**:
   - Clone the Space repository and copy your files into it, OR add the Space as a remote to your existing git repo.
   - **Option A (Add Remote)**:
     ```bash
     git remote add space https://huggingface.co/spaces/YOUR_USERNAME/acc-telemetry-backend
     git push space main
     ```
     *(Note: You might need to force push if histories differ, or pull first.)*

3. **Wait for Build**:
   - The "Building" status will appear on your Space page.
   - Once "Running", your API is live at `https://YOUR_USERNAME-acc-telemetry-backend.hf.space`.
   - Interactive docs: `https://YOUR_USERNAME-acc-telemetry-backend.hf.space/docs`

## Frontend (optional / not in repo)

A separate React frontend is **not currently included** in this repository. You can:

- Call the API via Swagger UI (`/docs`) or any HTTP client
- Use the CLI workflow: `python main.py`
- Deploy your own client against the Space URL if you build one later

## Important Notes

- **Ephemeral Storage**: Videos uploaded to the backend will be **deleted** if the Space restarts (after inactivity or new deployments).
- **Public Access**: By default Spaces are public. Make the Space private in Settings if needed, and handle auth for any client.
