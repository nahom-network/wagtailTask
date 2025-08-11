from django.core.paginator import Paginator
from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

# Create your models here.


class NewsArticle(Page):
    publication_date = models.DateTimeField()
    summary = models.TextField()
    source_url = models.URLField()

    content_panels = Page.content_panels + [
        FieldPanel("publication_date"),
        FieldPanel("summary"),
        FieldPanel("source_url"),
    ]

    parent_page_types = ["news.NewsListPage"]
    subpage_types = []




class NewsListPage(Page):
    # Ensure this model uses the styled template we edited
    template = "news/news_list_page.html"
    subpage_types = ["news.NewsArticle"]

    def get_context(self, request):
        context = super().get_context(request)
        queryset = (
            NewsArticle.objects.child_of(self)
            .live()
            .order_by("-publication_date")
        )

        # Paginate articles; 9 per page by default for a nice grid
        paginator = Paginator(queryset, 9)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["is_paginated"] = page_obj.has_other_pages()
        # Back-compat: expose current page list as "articles"
        context["articles"] = page_obj
        return context