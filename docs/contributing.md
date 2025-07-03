# Contributing

Thank you for considering a contribution! The steps below outline the typical
workflow:

1. Create a Python virtual environment and install dependencies:

   ```bash
   ./setup_env.sh
   source venv/bin/activate
   ```

2. Install frontend packages and build the static assets:

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
