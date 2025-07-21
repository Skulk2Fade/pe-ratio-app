# Localization

MarketMinder uses [Flask-Babel](https://babel.pocoo.org/) for translations. Each language lives in its own subfolder inside `translations/`.

## Adding a new language

1. Ensure the `Babel` CLI is installed (`pip install Babel`).
2. Extract messages and create the language folder:
   ```bash
   pybabel extract -F babel.cfg -o messages.pot .
   pybabel init -d translations -i messages.pot -l <lang>
   ```
3. Translate the generated `messages.po` file under `translations/<lang>/LC_MESSAGES/`.
4. Compile the catalog so Flask can load it:
   ```bash
   pybabel compile -d translations
   ```

Feel free to open a pull request with the new `.po` file so others can benefit from your translations.
