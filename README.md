# Small-donor money in the midterms

A static site comparing small-donor (unitemized) fundraising by party, state and candidate.
Data comes from FEC filings via the OpenFEC API and refreshes automatically every day.

## Set up (about 10 minutes)
1. Get a free API key at https://api.open.fec.gov/developers/
2. Create a new public repository on GitHub and upload everything in this folder
   (including the hidden `.github` folder; easiest with GitHub Desktop or `git push`).
3. Repo Settings > Secrets and variables > Actions > New repository secret.
   Name: `FEC_API_KEY`, value: your key.
4. Repo Settings > Pages > Build from branch > `main` / root > Save.
5. Actions tab > "Update FEC data" > Run workflow. The first run can take several minutes.
6. Your site will be at `https://YOUR-USERNAME.github.io/YOUR-REPO/`.

To track more election years, add them to the `python fetch_fec.py` line in
`.github/workflows/update.yml`.
