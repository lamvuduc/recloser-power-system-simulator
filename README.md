# Automatic Recloser Simulator

Educational Flask web app for demonstrating automatic circuit reclosing.

## Local run

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Public sharing

The project is prepared for Render.

1. Create a GitHub repository.
2. Upload all files in this folder to the repository root.
3. On Render choose **New → Blueprint** and connect the GitHub repository.
4. Render reads `render.yaml`, installs `requirements.txt`, and starts Gunicorn.
5. Share the resulting `https://...onrender.com` URL.

The app has no database and each visitor's simulation is independent. No user login is required.

Render free web services can spin down after 15 minutes of inactivity, so the first request after inactivity may take longer. See Render documentation for current limits.

## Important

This is an educational simulation, not a protection/control system for real electrical equipment.
