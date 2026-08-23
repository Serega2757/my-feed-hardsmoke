name: HardSmoke feed

on:
  schedule:
    # Каждые 30 минут. GitHub выполняет cron с задержкой до нескольких минут —
    # это нормально и на импорт в OneBox не влияет.
    - cron: "*/30 * * * *"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: hardsmoke-feed
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Generate feed.xml
        env:
          SPREADSHEET_ID: ${{ secrets.GMALL_SPREADSHEET_ID }}
        run: python generate_hardsmoke_feed.py

      - name: Commit feed.xml
        run: |
          if git diff --quiet -- feed.xml; then
            echo "Без изменений — коммит не нужен"
            exit 0
          fi
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add feed.xml
          git commit -m "update feed.xml"
          git push
