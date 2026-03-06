import django_filters

from practices.models import Practice


class PracticeFilter(django_filters.FilterSet):
    subject = django_filters.NumberFilter(field_name="subject__subject_id")
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    address = django_filters.CharFilter(field_name="employer__address", lookup_expr="icontains")
    company_name = django_filters.CharFilter(field_name="employer__company_name", lookup_expr="icontains")
    active_only = django_filters.BooleanFilter(field_name="is_active")
    favorites = django_filters.BooleanFilter(method="filter_favorites")

    class Meta:
        model = Practice
        fields = [
            "subject",
            "title",
            "address",
            "company_name",
            "approval_status",
            "progress_status",
            "active_only",
            "favorites",
        ]

    def filter_favorites(self, queryset, name, value):
        if value and hasattr(self.request.user, "favorite_practices"):
            return queryset.filter(pk__in=self.request.user.favorite_practices.values_list("pk", flat=True))
        return queryset
