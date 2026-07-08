"""
Tests for subject.admin — C5.H1: min_hours in list_display and list_filter.
"""

from django.test import TestCase

from subject.admin import SubjectAdmin


class SubjectAdminTest(TestCase):
    """C5.H1: Verify min_hours is in SubjectAdmin list_display and list_filter."""

    def test_min_hours_in_list_display(self):
        """min_hours must be in SubjectAdmin.list_display."""
        self.assertIn("min_hours", SubjectAdmin.list_display, "min_hours must be in list_display (C5.H1)")

    def test_min_hours_in_list_filter(self):
        """min_hours must be in SubjectAdmin.list_filter."""
        self.assertIn("min_hours", SubjectAdmin.list_filter, "min_hours must be in list_filter (C5.H1)")
