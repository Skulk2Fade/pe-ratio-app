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
   npm install
   npm run build
   ```

3. Run the unit tests and style checks before committing:

   ```bash
   pytest
   black --check .
   flake8
   ```

4. Open a pull request describing your changes.
