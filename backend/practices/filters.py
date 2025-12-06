import django_filters
from api.models import Practice


class PracticeFilter(django_filters.FilterSet):
    subject = django_filters.NumberFilter(field_name="subject__subject_id")
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    address = django_filters.CharFilter(field_name="employer__address", lookup_expr="icontains")
    company_name = django_filters.CharFilter(field_name="employer__company_name", lookup_expr="icontains")
    active_only = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Practice
        fields = [
            "subject",
            "title",
            "address",
            "company_name",
            "approval_status",
            "progress_status",
        ]
