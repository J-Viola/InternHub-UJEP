# from django.shortcuts import render
from rest_framework.pagination import PageNumberPagination


# Create your views here.
# -------------------------------------------------------------
# Nastavení vlastní stránkovací třídy pro všechny viewsety
# -------------------------------------------------------------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
