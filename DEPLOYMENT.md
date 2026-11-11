# Deploying mattkeen.com Data Lab (GitHub + Railway + Wix DNS)

## 1. Run it on Windows

Unzip the project. In PowerShell, `cd` to the directory containing `run.py`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Visit http://127.0.0.1:5000/. Stop with Ctrl+C.

Optional tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 2. Publish to GitHub

Create an empty repository named `mattkeen-data-lab` (don't initialize a README because one already exists). Open PowerShell in the project folder:

```powershell
git init
git add .
git commit -m "Initial Data Lab site"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mattkeen-data-lab.git
git push -u origin main
```

Replace YOUR_USERNAME. Sign in to GitHub when prompted. The `.gitignore` excludes `.venv` and local bytecode.

## 3. Deploy on Railway

- In Railway, create a **New Project** -> **Deploy from GitHub repo**.
- Connect the `mattkeen-data-lab` repository.
- Let Railpack install dependencies from `requirements.txt`.
- Set the Railway service Start Command to `sh -c 'gunicorn --bind 0.0.0.0:${PORT:-8000} wsgi:app'` if the platform does not detect and run the Procfile correctly.
- Under service Settings -> Networking, choose **Generate Domain**.
- Check the generated `*.up.railway.app` address before touching domain DNS.

## 4. Connect mattkeen.com

- In the same Railway service, under Settings -> Networking -> Custom Domain, add `mattkeen.com`, and separately `www.mattkeen.com` if desired.
- Railway displays DNS records to create. **Copy the exact values Railway gives you; do not guess.**
- Wherever the domain's DNS is managed (Wix, if it still holds DNS for the domain), open DNS Records and create/replace the conflicting root (`@` / blank host) and `www` A/CNAME records as specified by Railway.
- Keep existing MX, SPF, DKIM, DMARC and unrelated TXT records; those may be required for email and domain verification.
- Allow time for DNS propagation and Railway TLS certificate provisioning; test both domain variants.
- Caution: moving the root/www domain will replace the existing public site. Back up any content and confirm the Railway preview before changing DNS.

## 5. Update after deployment

Edit templates under `app/templates/`, CSS in `app/static/css/site.css`, and charts/behavior in `app/static/js/site.js`. Check locally, then:

```powershell
git add .
git commit -m "Describe the update"
git push
```

Railway automatically builds and deploys commits from the connected GitHub branch.

## 6. Data integrity

`app/data/rail_routes.json` contains **illustrative** figures. Do not remove the prototype-data disclaimers before replacing these values with validated FRA data. `scripts/fra_etl.py` is only a scaffold, not a complete ingestion pipeline.
