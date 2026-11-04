import datetime
from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Choice, Question, UserProfile, Category, Vote

User = get_user_model()


class QuestionModelTests(TestCase):
    def test_was_published_recently_with_future_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future.
        """
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is older than 1 day.
        """
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """
        was_published_recently() returns True for questions whose pub_date
        is within the last day.
        """
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)


def create_question(question_text, days):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


class QuestionIndexViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser@example.com", email="testuser@example.com", password="password")
        self.client.force_login(self.user)

    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past are displayed on the
        index page.
        """
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "No polls are available.")
        self.assertQuerySetEqual(response.context["latest_question_list"], [])

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question],
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse("polls:index"))
        self.assertQuerySetEqual(
            response.context["latest_question_list"],
            [question2, question1],
        )


class QuestionDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser@example.com", email="testuser@example.com", password="password")
        self.client.force_login(self.user)

    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text="Future question.", days=5)
        url = reverse("polls:detail", args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text="Past Question.", days=-5)
        url = reverse("polls:detail", args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


class RoleAccessControlTests(TestCase):
    def setUp(self):
        # Create users corresponding to email role rules
        self.super_admin = User.objects.create_user(
            username="superadmin@gmail.com",
            email="superadmin@gmail.com",
            password="password"
        )
        self.admin = User.objects.create_user(
            username="myadmin@gmail.com",
            email="myadmin@gmail.com",
            password="password"
        )
        self.voter = User.objects.create_user(
            username="voter@example.com",
            email="voter@example.com",
            password="password"
        )

    def test_email_based_role_assignment(self):
        """Verify that user profiles and roles are mapped correctly based on email rules."""
        self.super_admin.refresh_from_db()
        self.admin.refresh_from_db()
        self.voter.refresh_from_db()

        self.assertEqual(self.super_admin.profile.role, "SUPER_ADMIN")
        self.assertTrue(self.super_admin.is_superuser)
        self.assertTrue(self.super_admin.is_staff)

        self.assertEqual(self.admin.profile.role, "ADMIN")
        self.assertFalse(self.admin.is_superuser)
        self.assertTrue(self.admin.is_staff)

        self.assertEqual(self.voter.profile.role, "USER")
        self.assertFalse(self.voter.is_superuser)
        self.assertFalse(self.voter.is_staff)

    def test_super_admin_route_guards(self):
        """Verify that only Super Admins can access Super Admin pages."""
        # Super Admin access
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:super_admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Admin access (403)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:super_admin_dashboard"))
        self.assertEqual(response.status_code, 403)

        # Voter access (403)
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:super_admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_route_guards(self):
        """Verify that only Admins can access Admin pages."""
        # Admin access
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Super Admin access — allowed (higher privilege includes admin access)
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Voter access (403)
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_voter_route_guards(self):
        """Verify that only voters (USER role) can access voter pages."""
        # Voter access
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:user_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Super Admin access redirects to super admin dashboard
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:user_dashboard"))
        self.assertRedirects(response, reverse("polls:super_admin_dashboard"))

        # Admin access redirects to admin dashboard
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:user_dashboard"))
        self.assertRedirects(response, reverse("polls:admin_dashboard"))


class AdminPollingModuleTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="superadmin@gmail.com",
            email="superadmin@gmail.com",
            password="password"
        )
        self.admin = User.objects.create_user(
            username="myadmin@gmail.com",
            email="myadmin@gmail.com",
            password="password"
        )
        self.voter = User.objects.create_user(
            username="voter@example.com",
            email="voter@example.com",
            password="password"
        )
        self.category = Category.objects.create(name="Tech", description="Technology surveys")

    def test_unauthorized_user_access(self):
        """Verify that USER role (voters) cannot access admin polling routes."""
        self.client.force_login(self.voter)
        
        # Test access to list, create, edit, delete
        response = self.client.get(reverse("polls:admin_polls_list"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("polls:admin_polls_create"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("polls:admin_polls_categories"))
        self.assertEqual(response.status_code, 403)

    def test_admin_create_poll(self):
        """Verify that admins can create polls with custom choices."""
        self.client.force_login(self.admin)
        post_data = {
            "question_text": "What is your favorite language?",
            "description": "Programming languages comparison",
            "category": self.category.id,
            "poll_type": "single",
            "visibility": "public",
            "status": "draft",
            "choices": ["Python", "JavaScript", "Go"]
        }
        response = self.client.post(reverse("polls:admin_polls_create"), post_data)
        self.assertRedirects(response, reverse("polls:admin_polls_list"))

        # Verify creation in DB
        poll = Question.objects.get(question_text="What is your favorite language?")
        self.assertEqual(poll.description, "Programming languages comparison")
        self.assertEqual(poll.category, self.category)
        self.assertEqual(poll.status, "draft")
        self.assertEqual(poll.choice_set.count(), 3)

    def test_admin_edit_poll(self):
        """Verify that admins can edit polls and sync choices."""
        poll = Question.objects.create(
            question_text="Original Poll",
            pub_date=timezone.now(),
            status="draft"
        )
        Choice.objects.create(question=poll, choice_text="Choice A")
        Choice.objects.create(question=poll, choice_text="Choice B")

        self.client.force_login(self.admin)
        post_data = {
            "question_text": "Updated Poll Name",
            "description": "Updated Description",
            "poll_type": "multiple",
            "visibility": "private",
            "status": "active",
            "choices": ["Choice A", "Choice C"]  # Choice B is removed, Choice C is added
        }
        
        response = self.client.post(reverse("polls:admin_polls_edit", args=(poll.id,)), post_data)
        self.assertRedirects(response, reverse("polls:admin_polls_list"))

        poll.refresh_from_db()
        self.assertEqual(poll.question_text, "Updated Poll Name")
        self.assertEqual(poll.status, "active")
        self.assertEqual(poll.choice_set.count(), 2)
        self.assertQuerySetEqual(
            poll.choice_set.order_by('choice_text'),
            ["Choice A", "Choice C"],
            transform=lambda c: c.choice_text
        )

    def test_admin_delete_poll(self):
        """Verify that admins can delete polls."""
        poll = Question.objects.create(
            question_text="To Delete",
            pub_date=timezone.now()
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("polls:admin_polls_delete", args=(poll.id,)))
        self.assertRedirects(response, reverse("polls:admin_polls_list"))
        self.assertFalse(Question.objects.filter(id=poll.id).exists())

    def test_poll_lifecycle_actions(self):
        """Verify publishing and closing of polls."""
        poll = Question.objects.create(
            question_text="Lifecycle Poll",
            pub_date=timezone.now(),
            status="draft"
        )
        self.client.force_login(self.admin)

        # 1. Publish (draft -> active)
        response = self.client.get(reverse("polls:admin_polls_publish", args=(poll.id,)))
        self.assertRedirects(response, reverse("polls:admin_polls_list"))
        poll.refresh_from_db()
        self.assertEqual(poll.status, "active")
        self.assertIsNotNone(poll.start_date)

        # 2. Close (active -> closed)
        response = self.client.get(reverse("polls:admin_polls_close", args=(poll.id,)))
        self.assertRedirects(response, reverse("polls:admin_polls_list"))
        poll.refresh_from_db()
        self.assertEqual(poll.status, "closed")
        self.assertIsNotNone(poll.end_date)

    def test_duplicate_poll(self):
        """Verify that a poll can be duplicated as a draft with 0 votes."""
        poll = Question.objects.create(
            question_text="Base Poll",
            pub_date=timezone.now(),
            status="active"
        )
        Choice.objects.create(question=poll, choice_text="Option X", votes=42)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:admin_polls_duplicate", args=(poll.id,)))
        self.assertRedirects(response, reverse("polls:admin_polls_list"))

        # Verify duplicated draft poll
        dup = Question.objects.get(question_text="Copy of Base Poll")
        self.assertEqual(dup.status, "draft")
        self.assertEqual(dup.choice_set.count(), 1)
        self.assertEqual(dup.choice_set.first().choice_text, "Option X")
        self.assertEqual(dup.choice_set.first().votes, 0)

    def test_category_crud_operations(self):
        """Verify creation, edit, and deletion of categories."""
        self.client.force_login(self.admin)

        # 1. Create Category
        response = self.client.post(reverse("polls:admin_category_create"), {
            "name": "Politics",
            "description": "Election surveys"
        })
        self.assertRedirects(response, reverse("polls:admin_polls_categories"))
        self.assertTrue(Category.objects.filter(name="Politics").exists())

        # 2. Edit Category
        cat = Category.objects.get(name="Politics")
        response = self.client.post(reverse("polls:admin_category_edit", args=(cat.id,)), {
            "name": "Global Politics",
            "description": "Updated desc"
        })
        self.assertRedirects(response, reverse("polls:admin_polls_categories"))
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Global Politics")

        # 3. Delete Category
        response = self.client.post(reverse("polls:admin_category_delete", args=(cat.id,)))
        self.assertRedirects(response, reverse("polls:admin_polls_categories"))
        self.assertFalse(Category.objects.filter(id=cat.id).exists())


class SimpleRBACModuleTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username="superadmin@gmail.com",
            email="superadmin@gmail.com",
            password="password"
        )
        self.admin = User.objects.create_user(
            username="myadmin@gmail.com",
            email="myadmin@gmail.com",
            password="password"
        )
        self.voter = User.objects.create_user(
            username="voter@example.com",
            email="voter@example.com",
            password="password"
        )
        self.question = Question.objects.create(
            question_text="Sample Poll?",
            pub_date=timezone.now(),
            status="active"
        )
        self.choice = Choice.objects.create(question=self.question, choice_text="Yes", votes=0)

    def test_voter_cannot_double_vote(self):
        """Verify that a voter cannot vote twice on the same poll."""
        self.client.force_login(self.voter)
        
        # Vote 1: success
        response = self.client.post(reverse("polls:vote", args=(self.question.id,)), {"choice": self.choice.id})
        self.assertRedirects(response, reverse("polls:results", args=(self.question.id,)))
        self.assertEqual(Vote.objects.count(), 1)
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 1)

        # Vote 2: rejected/redirected with error message
        response = self.client.post(reverse("polls:vote", args=(self.question.id,)), {"choice": self.choice.id})
        self.assertRedirects(response, reverse("polls:results", args=(self.question.id,)))
        # Vote count remains 1
        self.assertEqual(Vote.objects.count(), 1)
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 1)

    def test_voter_can_view_history(self):
        """Verify that voting creates history records accessible to the voter."""
        self.client.force_login(self.voter)
        Vote.objects.create(user=self.voter, question=self.question, choice=self.choice)
        
        response = self.client.get(reverse("polls:user_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.question.question_text)
        self.assertContains(response, self.choice.choice_text)

    def test_only_admin_super_admin_access_analytics(self):
        """Verify that voters cannot access analytics views while admins can."""
        # 1. Voter gets 403
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:admin_analytics"))
        self.assertEqual(response.status_code, 403)

        # 2. Admin gets 200
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:admin_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_super_admin_admin_management_crud(self):
        """Verify that Super Admins can manage Admin accounts."""
        self.client.force_login(self.super_admin)

        # 1. List admins
        response = self.client.get(reverse("polls:super_admin_admins"))
        self.assertEqual(response.status_code, 200)

        # 2. Create Admin
        post_data = {
            "email": "newadmin@admin.com",  # triggers validation error because it must end with admin@gmail.com
            "first_name": "New",
            "last_name": "Admin",
            "password": "AdminPassword123"
        }
        response = self.client.post(reverse("polls:super_admin_admins_create"), post_data)
        self.assertEqual(response.status_code, 200)  # form validation fails, renders form again

        post_data["email"] = "newadminadmin@gmail.com"  # valid email ending
        response = self.client.post(reverse("polls:super_admin_admins_create"), post_data)
        self.assertRedirects(response, reverse("polls:super_admin_admins"))
        
        admin_user = User.objects.get(email="newadminadmin@gmail.com")
        self.assertEqual(admin_user.profile.role, "ADMIN")

        # 3. Edit Admin
        edit_data = {
            "email": "updatedadminadmin@gmail.com",
            "first_name": "Updated",
            "last_name": "AdminName",
            "password": ""  # keep existing password
        }
        response = self.client.post(reverse("polls:super_admin_admins_edit", args=(admin_user.id,)), edit_data)
        self.assertRedirects(response, reverse("polls:super_admin_admins"))
        admin_user.refresh_from_db()
        self.assertEqual(admin_user.email, "updatedadminadmin@gmail.com")

        # 4. Delete Admin
        response = self.client.post(reverse("polls:super_admin_admins_delete", args=(admin_user.id,)))
        self.assertRedirects(response, reverse("polls:super_admin_admins"))
        self.assertFalse(User.objects.filter(id=admin_user.id).exists())


class GoogleSSOModuleTests(TestCase):
    def test_google_login_not_configured(self):
        """Verify that google_login returns 400 Bad Request if GOOGLE_CLIENT_ID is not configured."""
        with self.settings(GOOGLE_CLIENT_ID=""):
            response = self.client.get(reverse("google_login"))
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Google SSO is not configured", response.content)

    def test_google_login_configured(self):
        """Verify that google_login redirects to Google authorization URL when client ID is set."""
        with self.settings(GOOGLE_CLIENT_ID="dummy-id"):
            response = self.client.get(reverse("google_login"))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("https://accounts.google.com/o/oauth2/v2/auth"))
            self.assertIn("client_id=dummy-id", response.url)


class StaticPagesModuleTests(TestCase):
    def test_static_pages_get(self):
        """Verify that all newly registered static pages load successfully."""
        pages = ["about_us", "help_center", "privacy_policy", "terms_of_service", "contact_us", "faq", "feedback"]
        for page in pages:
            response = self.client.get(reverse(page))
            self.assertEqual(response.status_code, 200)

    def test_contact_us_post_valid(self):
        """Verify that submitting the Contact Us form works correctly."""
        post_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Hello, I need help with custom reports."
        }
        response = self.client.post(reverse("contact_us"), post_data)
        self.assertRedirects(response, reverse("contact_us"))

    def test_contact_us_post_invalid(self):
        """Verify that submitting Contact Us form with missing values sets error."""
        post_data = {
            "name": "",
            "email": "jane@example.com",
            "message": ""
        }
        response = self.client.post(reverse("contact_us"), post_data)
        self.assertRedirects(response, reverse("contact_us"))

    def test_feedback_post_valid(self):
        """Verify that submitting the Feedback form with rating works."""
        post_data = {
            "rating": "5",
            "comments": "Love the user interface."
        }
        response = self.client.post(reverse("feedback"), post_data)
        self.assertRedirects(response, reverse("feedback"))

    def test_feedback_post_invalid(self):
        """Verify that submitting Feedback form without rating sets error."""
        post_data = {
            "rating": "",
            "comments": "Love the user interface."
        }
        response = self.client.post(reverse("feedback"), post_data)
        self.assertRedirects(response, reverse("feedback"))


class AnalyticsReportTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            username="superadmin@gmail.com", email="superadmin@gmail.com", password="password"
        )
        self.admin = User.objects.create_user(
            username="admin01admin@gmail.com", email="admin01admin@gmail.com", password="password"
        )
        self.voter = User.objects.create_user(
            username="user01@gmail.com", email="user01@gmail.com", password="password"
        )

    def test_download_report_access(self):
        """Verify that only authorized roles (Admin, Super Admin) can download analytics report."""
        # 1. Super Admin access
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:download_analytics_report"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(b"VOTEHUB PLATFORM ANALYTICS REPORT", response.content)

        # 2. Admin access
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:download_analytics_report"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # 3. Voter access (403 Forbidden)
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:download_analytics_report"))
        self.assertEqual(response.status_code, 403)

    def test_download_report_with_null_pub_date(self):
        """Verify that download_analytics_report works correctly when a question has no pub_date."""
        # Create a draft question with no pub_date
        Question.objects.create(question_text="Draft question without pub date", pub_date=None, status="draft")
        
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:download_analytics_report"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn(b"Draft question without pub date", response.content)
        self.assertIn(b"Not Published", response.content)

    def test_analytics_print_report_access(self):
        """Verify that the printable analytics report is accessible only to admins/superadmins."""
        # 1. Super Admin access
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("polls:admin_analytics_report"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "polls/admin_analytics_report.html")

        # 2. Admin access
        self.client.force_login(self.admin)
        response = self.client.get(reverse("polls:admin_analytics_report"))
        self.assertEqual(response.status_code, 200)

        # 3. Voter access (403 Forbidden)
        self.client.force_login(self.voter)
        response = self.client.get(reverse("polls:admin_analytics_report"))
        self.assertEqual(response.status_code, 403)






