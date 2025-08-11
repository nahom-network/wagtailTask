from django.core.management.base import BaseCommand

from news.models import NewsArticle, NewsListPage
from news.scraper.bbc_scraper import BBCNewsArticles


class Command(BaseCommand):
    help = "Scrape Hacker News and insert articles into Wagtail"

    def handle(self, *args, **options):
        """Handle the command to scrape BBC News and save articles."""
        scraper = BBCNewsArticles()
        articles = scraper.run_scraper()
        if not articles:
            self.stdout.write(self.style.WARNING("No articles scraped."))
            return

        news_list_page = NewsListPage.objects.first()
        if not news_list_page:
            self.stdout.write(self.style.ERROR("No NewsListPage found."))
            return

        for art in articles:
            if NewsArticle.objects.filter(title=art["title"]).exists():
                self.stdout.write(f"Skipping existing: {art['title']}")
                continue

            page = NewsArticle(
                title=art["title"],
                publication_date=art["publication_date"],
                summary=art["summary"],
                source_url=art["source_url"],
            )

            # Add as child page under NewsListPage
            news_list_page.add_child(instance=page)
            page.save_revision().publish()

            self.stdout.write(self.style.SUCCESS(f"Added: {art['title']}"))
