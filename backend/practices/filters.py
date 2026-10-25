import django_filters
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError

from practices.models import EMPLOYMENT_TYPE_CHOICES, Practice


class PracticeFilter(django_filters.FilterSet):
    subject = django_filters.NumberFilter(field_name="subject__subject_id")
    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    address = django_filters.CharFilter(field_name="employer__address", lookup_expr="icontains")
    company_name = django_filters.CharFilter(field_name="employer__company_name", lookup_expr="icontains")
    skills = django_filters.CharFilter(method="filter_skills")
    technologies = django_filters.CharFilter(method="filter_skill_category")
    tools = django_filters.CharFilter(method="filter_skill_category")
    methodologies = django_filters.CharFilter(method="filter_skill_category")
    city = django_filters.CharFilter(field_name="city", lookup_expr="icontains")
    region = django_filters.CharFilter(field_name="region", lookup_expr="exact")
    # BL-05 / RF-02a — explicitní filtr typu úvazku (employment type).
    # Závazný číselník dle guarantor-values.md §1 (2026-10-11); neznámá
    # hodnota → 400 (validate), prázdná hodnota → beze změny
    # (Filter.filter → EMPTY_VALUES). Přesná shoda (exact) beze změny.
    employment_type = django_filters.CharFilter(method="filter_employment_types", label="Typ úvazku")
    semester = django_filters.CharFilter(method="filter_semesters")
    active_only = django_filters.BooleanFilter(field_name="is_active")
    favorites = django_filters.BooleanFilter(method="filter_favorites")
    min_duration = django_filters.NumberFilter(method="filter_min_duration")
    max_duration = django_filters.NumberFilter(method="filter_max_duration")
    has_capacity = django_filters.BooleanFilter(method="filter_has_capacity")

    class Meta:
        model = Practice
        fields = [
            "subject",
            "title",
            "address",
            "company_name",
            "skills",
            "technologies",
            "tools",
            "methodologies",
            "semester",
            "region",
            "employment_type",
            "approval_status",
            "progress_status",
            "active_only",
            "favorites",
            "min_duration",
            "max_duration",
            "has_capacity",
        ]

    def filter_skills(self, queryset, name, value):
        if value:
            qs = queryset
            for skill in self._values(value):
                qs = qs.filter(skills__icontains=skill)
            return qs
        return queryset

    @staticmethod
    def _values(value):
        return [item.strip() for item in str(value).split(",") if item.strip()]

    def filter_skill_category(self, queryset, name, value):
        values = self._values(value)
        if not values:
            return queryset
        # OR uvnitř kategorie; JSON contains funguje pro současný kategoriální
        # tvar i legacy seznam, který migrace přesune do technologies.
        condition = Q()
        for item in values:
            condition |= Q(**{f"skills__{name}__icontains": item})
        return queryset.filter(condition)

    def filter_employment_types(self, queryset, name, value):
        values = self._values(value)
        allowed = {key for key, _ in EMPLOYMENT_TYPE_CHOICES}
        invalid = set(values) - allowed
        if invalid:
            raise ValidationError(f"Neplatný typ úvazku: {', '.join(sorted(invalid))}")
        return queryset.filter(employment_type__in=values) if values else queryset

    def filter_semesters(self, queryset, name, value):
        values = self._values(value)
        invalid = set(values) - {"ZS", "LS"}
        if invalid:
            raise ValidationError(f"Neplatný semestr: {', '.join(sorted(invalid))}")
        return queryset.filter(semester__in=values) if values else queryset

    def filter_favorites(self, queryset, name, value):
        if value and hasattr(self.request.user, "favorite_practices"):
            return queryset.filter(pk__in=self.request.user.favorite_practices.values_list("pk", flat=True))
        return queryset

    def filter_min_duration(self, queryset, name, value):
        if value is not None:
            return queryset.filter(subject__min_hours__gte=value)
        return queryset

    def filter_max_duration(self, queryset, name, value):
        if value is not None:
            return queryset.filter(subject__min_hours__lte=value)
        return queryset

    def filter_has_capacity(self, queryset, name, value):
        if value:
            # available_positions IS NULL OR available_positions > approved_count
            return queryset.filter(Q(available_positions__isnull=True) | Q(available_positions__gt=F("approved_count")))
        elif value is False:
            return queryset.filter(
                available_positions__isnull=False,
                available_positions__lte=F("approved_count"),
            )
        return queryset
