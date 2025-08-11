# Wagtail News Scraper Demo

A Wagtail (Django) project that scrapes BBC Innovation/Technology headlines and publishes articles as Wagtail pages. Includes a styled list page with pagination.

## Prerequisites
- Python 3.13 (project uses a local venv)
- Git (optional)
- Node is NOT required

## Quick start

1. Create and activate a virtual environment
   - Windows PowerShell
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. Install dependencies
   ```powershell
   pip install -r requirements.txt
   ```

3. Create the database and a superuser
   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Run the development server
   ```powershell
   python manage.py runserver
   ```
   Visit http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/ (login with the superuser you created).

## Wagtail setup
1. In the admin, create a new page of type “News List Page” at the root.
2. Publish it. Its URL will display the styled list with pagination.

## Scraping BBC articles
The project includes a management command to fetch and publish articles under your News List Page.

- Fetch and publish:
  ```powershell
  python manage.py scrape_news
  ```

What it does:
- Scrapes https://www.bbc.com/innovation/technology for headlines.
- Follows each headline to extract title, date, and summary (robust to HTML changes).
- Creates child pages of type `NewsArticle` under your first `NewsListPage`.
- Skips duplicates by title.

## Pagination
The News List Page template displays articles with accessible pagination controls. Page size is defined in the backend and can be adjusted in `NewsListPage.get_context` if needed.

## Project layout
- `news/models.py`: Wagtail page models (`NewsListPage`, `NewsArticle`).
- `news/templates/news/news_list_page.html`: List page template.
- `wagtailTask/static/css/wagtailTask.css`: Global styles (news list styles are scoped under `.news-list`).
- `news/scraper/bbc_scraper.py`: Scraper with resilient parsing.
- `news/management/commands/fetch_bbc_news.py`: Management command to run the scraper and publish pages.

## Troubleshooting
- Static files not styling the page? Ensure `DEBUG=True` (default in dev) and the base template includes `{% load static %}` and the stylesheet link. This project already does via `wagtailTask/templates/base.html`.
- No `NewsListPage` found when running the command: Create and publish one in the Wagtail admin first.
- SSL or connection errors when scraping: Re-run the command later; the scraper has small retries and fallbacks.

## License
This repository is for learning/demo purposes.
