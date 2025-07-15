# Contributing

Thank you for considering a contribution! The steps below outline the typical
workflow:

1. Create a Python virtual environment and install dependencies. The
   easiest way is to run the bootstrap script which also installs the
   frontend packages:

   ```bash
   ./scripts/bootstrap.sh
   source venv/bin/activate
   ```

   The previous `setup_env.sh` script remains available if you prefer
   to manage the Node dependencies separately.

2. If you skip the bootstrap script, install the frontend packages and
   build the static assets manually:

   ```bash
   npm ci
   npm run build
   ```
   The `package.json` file pins Bootstrap and Plotly versions so `npm ci`
   installs exactly those dependencies for reproducible builds.

3. Install the git hooks so formatting and linting run automatically:

   ```bash
   pre-commit install
   ```

4. Run the unit tests before committing:

   ```bash
   pytest
   ```

5. Optionally check static types with mypy:

   ```bash
   mypy app.py stockapp
   ```

6. Open a pull request describing your changes.
