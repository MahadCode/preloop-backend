from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import EmailVerificationToken, PasswordResetToken
from discussions.models import Comment, Report, Solution
from moderation.models import ModerationReport
from notifications.models import Notification
from progress.models import PreparationGoal
from questions.models import Question, UserQuestionStatus
from taxonomy.models import Company, JobRole, Tag
from voting.models import Vote

User = get_user_model()
PASSWORD = "PrepLoop-test-1"


def html(*paragraphs):
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


class Command(BaseCommand):
    help = "Insert structured PrepLoop records into every application table. Safe to run again."

    @transaction.atomic
    def handle(self, *args, **options):
        users = self.seed_users()
        companies = self.seed_named(Company, [
            "Northwind",
            "Contoso",
            "Google",
            "Amazon",
            "Meta",
            "Microsoft",
            "Stripe",
            "Netflix",
        ])
        roles = self.seed_named(JobRole, [
            "Backend Engineer",
            "Platform Engineer",
            "Frontend Engineer",
            "Data Engineer",
            "Site Reliability Engineer",
        ])
        tags = self.seed_named(Tag, [
            "Systems",
            "Caching",
            "Databases",
            "API Design",
            "Concurrency",
            "Networking",
            "Observability",
            "Message Queues",
        ])
        questions = self.seed_questions(users, companies, roles, tags)
        solutions = self.seed_solutions(users, questions)
        comments = self.seed_comments(users, questions, solutions)
        reports = self.seed_reports(users, questions, solutions, comments)
        self.seed_votes(users, questions)
        self.seed_statuses(users, questions)
        goals = self.seed_goals(users, companies, tags)
        self.seed_notifications(users, questions, solutions, comments, goals)
        self.seed_tokens(users)

        self.stdout.write(self.style.SUCCESS("Seeded PrepLoop tables."))
        self.stdout.write(f"Users {User.objects.count()} · companies {Company.objects.count()} · roles {JobRole.objects.count()} · topics {Tag.objects.count()}")
        self.stdout.write(f"Questions {Question.objects.count()} · solutions {Solution.objects.count()} · comments {Comment.objects.count()} · votes {Vote.objects.count()}")
        self.stdout.write(f"Statuses {UserQuestionStatus.objects.count()} · goals {PreparationGoal.objects.count()} · reports {Report.objects.count()} · moderation {ModerationReport.objects.count()}")
        self.stdout.write(f"Notifications {Notification.objects.count()} · verification tokens {EmailVerificationToken.objects.count()} · reset tokens {PasswordResetToken.objects.count()}")
        self.stdout.write("Password for every seeded account: PrepLoop-test-1")
        self.stdout.write("Usernames: preploop, moderator, admin, avery, jordan, pending, suspended")

    def seed_users(self):
        specs = [
            ("preploop", "preploop@example.com", "+14155552671", "Preploop", "Tester", "user", "active", "Local PrepLoop test account."),
            ("moderator", "moderator@example.com", "+14155552672", "Moderator", "Tester", "moderator", "active", "Reviews reports and questions waiting for publication."),
            ("admin", "admin@example.com", "+14155552673", "Alex", "Okada", "admin", "active", "Keeps the taxonomy and member accounts in order."),
            ("avery", "avery@example.com", "+14155552674", "Avery", "Chen", "user", "active", "Backend engineer practicing system design three evenings a week."),
            ("jordan", "jordan@example.com", "+14155552675", "Jordan", "Hale", "user", "active", "Writes up solutions after mock interviews."),
            ("pending", "pending@example.com", "+14155552676", "Riley", "Nguyen", "user", "pending_verification", "Signed up and has not confirmed the email yet."),
            ("suspended", "suspended@example.com", "+14155552677", "Sam", "Patel", "user", "suspended", "Account is suspended and cannot use verified study tools."),
        ]
        users = {}
        for username, email, phone, first, last, role, status, bio in specs:
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User(
                    username=username,
                    email=email,
                    phone=phone,
                    first_name=first,
                    last_name=last,
                    bio=bio,
                    role=role,
                    account_status=status,
                )
                user.set_password(PASSWORD)
                user.save()
            users[username] = user
        return users

    def seed_named(self, model, names):
        records = {}
        for name in names:
            record, created = model.objects.get_or_create(name=name)
            if not created and not record.is_active and name != "Queues":
                record.is_active = True
                record.save(update_fields=["is_active"])
            records[name] = record
        return records

    def seed_questions(self, users, companies, roles, tags):
        specs = [
            {
                "title": "Design a rate limiter for an API",
                "author": "preploop",
                "difficulty": "easy",
                "status": "published",
                "deleted": False,
                "days_ago": 21,
                "role": "Backend Engineer",
                "companies": ["Northwind"],
                "tags": ["Systems"],
                "description": html(
                    "Explain token bucket versus sliding window, and how you would store counters.",
                    "Cover what happens when a client bursts, and where the limiter sits relative to the gateway.",
                ),
                "preserve": True,
            },
            {
                "title": "Review the cache invalidation plan",
                "author": "preploop",
                "difficulty": "medium",
                "status": "pending_review",
                "deleted": False,
                "days_ago": 2,
                "role": "Backend Engineer",
                "companies": ["Contoso"],
                "tags": ["Caching"],
                "description": html(
                    "A service caches user profiles for sixty seconds. Writes sometimes leave readers on the old profile.",
                    "Say which invalidation strategy you would use, and what you would measure after the change.",
                ),
                "preserve": True,
            },
            {
                "title": "Design a URL shortener",
                "author": "avery",
                "difficulty": "easy",
                "status": "published",
                "deleted": False,
                "days_ago": 18,
                "role": "Backend Engineer",
                "companies": ["Meta", "Amazon"],
                "tags": ["Databases", "API Design"],
                "description": html(
                    "Turn a long URL into a short key and resolve it back. Estimate read and write traffic separately.",
                    "Decide how keys are generated, how you avoid collisions, and what a custom alias changes.",
                ),
            },
            {
                "title": "Choose indexes for an orders table",
                "author": "jordan",
                "difficulty": "easy",
                "status": "published",
                "deleted": False,
                "days_ago": 16,
                "role": "Data Engineer",
                "companies": ["Microsoft"],
                "tags": ["Databases"],
                "description": html(
                    "Orders are filtered by customer, status, and created date. The table is already large.",
                    "Propose indexes, say which queries they serve, and which writes get more expensive.",
                ),
            },
            {
                "title": "Design a news feed",
                "author": "preploop",
                "difficulty": "medium",
                "status": "published",
                "deleted": False,
                "days_ago": 14,
                "role": "Backend Engineer",
                "companies": ["Meta", "Northwind"],
                "tags": ["Systems", "Caching"],
                "description": html(
                    "A member follows accounts and should see new posts within a few seconds.",
                    "Compare fan-out on write with fan-out on read, and say how you would rank the first page.",
                ),
            },
            {
                "title": "Design a distributed cache",
                "author": "avery",
                "difficulty": "medium",
                "status": "published",
                "deleted": False,
                "days_ago": 12,
                "role": "Platform Engineer",
                "companies": ["Amazon", "Netflix"],
                "tags": ["Caching", "Systems"],
                "description": html(
                    "Application servers need a shared cache with a bounded memory budget.",
                    "Cover partitioning, replication, and what a client does when a node is unreachable.",
                ),
            },
            {
                "title": "Debug a latency spike in checkout",
                "author": "jordan",
                "difficulty": "medium",
                "status": "published",
                "deleted": False,
                "days_ago": 11,
                "role": "Site Reliability Engineer",
                "companies": ["Stripe"],
                "tags": ["Observability", "Networking"],
                "description": html(
                    "Checkout p95 moved from 180ms to 900ms after a deploy. Errors did not increase.",
                    "Walk through the signals you would check first, and how you would decide whether to roll back.",
                ),
            },
            {
                "title": "Design a chat inbox",
                "author": "avery",
                "difficulty": "medium",
                "status": "published",
                "deleted": False,
                "days_ago": 9,
                "role": "Backend Engineer",
                "companies": ["Google", "Meta"],
                "tags": ["Message Queues", "Networking"],
                "description": html(
                    "Two people exchange messages and both see a delivered state. Presence can be a few seconds stale.",
                    "Describe storage for history, how a message reaches an offline client, and how you order them.",
                ),
            },
            {
                "title": "Design autocomplete for a product search",
                "author": "preploop",
                "difficulty": "medium",
                "status": "published",
                "deleted": False,
                "days_ago": 8,
                "role": "Frontend Engineer",
                "companies": ["Google"],
                "tags": ["API Design", "Caching"],
                "description": html(
                    "The search box should suggest products after two characters, without waiting on the full search index.",
                    "Describe the request path, what you cache, and how a newly added product becomes suggestible.",
                ),
            },
            {
                "title": "Design a payment ledger",
                "author": "jordan",
                "difficulty": "hard",
                "status": "published",
                "deleted": False,
                "days_ago": 7,
                "role": "Backend Engineer",
                "companies": ["Stripe"],
                "tags": ["Databases", "Concurrency"],
                "description": html(
                    "Every charge, refund, and payout is an immutable entry. Account balances are derived.",
                    "Explain idempotency keys, how two writers avoid a double charge, and how you rebuild a balance.",
                ),
            },
            {
                "title": "Shard a multi-tenant database",
                "author": "avery",
                "difficulty": "hard",
                "status": "published",
                "deleted": False,
                "days_ago": 6,
                "role": "Data Engineer",
                "companies": ["Amazon", "Microsoft"],
                "tags": ["Databases", "Systems"],
                "description": html(
                    "One tenant is much larger than the others, and a single primary is close to its write limit.",
                    "Choose a shard key, say how a tenant moves, and how a query that spans tenants is handled.",
                ),
            },
            {
                "title": "Design a video upload pipeline",
                "author": "jordan",
                "difficulty": "hard",
                "status": "published",
                "deleted": False,
                "days_ago": 4,
                "role": "Platform Engineer",
                "companies": ["Netflix"],
                "tags": ["Message Queues", "Observability"],
                "description": html(
                    "Clients upload large files. The service must transcode them and publish a playable rendition.",
                    "Cover retries, poison messages, and which metric tells you the pipeline is falling behind.",
                ),
            },
            {
                "title": "Design a feature flag service",
                "author": "avery",
                "difficulty": "medium",
                "status": "pending_review",
                "deleted": False,
                "days_ago": 1,
                "role": "Platform Engineer",
                "companies": ["Contoso"],
                "tags": ["API Design", "Systems"],
                "description": html(
                    "Services need a flag value on each request, and a change should reach them within a minute.",
                    "This draft is waiting for a moderator before it appears in the archive.",
                ),
            },
            {
                "title": "Draft notes on a private outage",
                "author": "jordan",
                "difficulty": "hard",
                "status": "removed",
                "deleted": False,
                "days_ago": 3,
                "role": "Site Reliability Engineer",
                "companies": ["Stripe"],
                "tags": ["Observability"],
                "description": html(
                    "This prompt was removed after review. The notes named an internal customer.",
                ),
            },
            {
                "title": "Withdrawn: sticky session notes",
                "author": "avery",
                "difficulty": "easy",
                "status": "removed",
                "deleted": True,
                "days_ago": 20,
                "role": "Backend Engineer",
                "companies": ["Northwind"],
                "tags": ["Networking"],
                "description": html(
                    "Withdrawn from the archive. Kept so deleted rows stay represented.",
                ),
            },
        ]
        questions = {}
        for spec in specs:
            question, created = Question.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "author": users[spec["author"]],
                    "difficulty_level": spec["difficulty"],
                    "status": spec["status"],
                    "is_deleted": spec["deleted"],
                    "job_role": roles[spec["role"]],
                    "description": spec["description"],
                },
            )
            if created or not spec.get("preserve"):
                if created or not question.company.exists():
                    question.company.set([companies[name] for name in spec["companies"]])
                if created or not question.tag.exists():
                    question.tag.set([tags[name] for name in spec["tags"]])
                if created or question.job_role_id is None:
                    question.job_role = roles[spec["role"]]
                    question.save(update_fields=["job_role"])
            Question.objects.filter(pk=question.pk).update(
                created_at=timezone.now() - timedelta(days=spec["days_ago"])
            )
            questions[spec["title"]] = question
        return questions

    def seed_solutions(self, users, questions):
        specs = [
            (
                "Design a rate limiter for an API",
                "preploop",
                "Use a token bucket stored in Redis with a key per client.",
            ),
            (
                "Design a URL shortener",
                "jordan",
                "Generate a base62 key from an increasing id. Store the pair in a unique index and redirect with a cache in front of the read path.",
            ),
            (
                "Design a news feed",
                "avery",
                "Fan out to active followers on write, and fall back to a read-time merge for accounts with a very large audience.",
            ),
            (
                "Design a payment ledger",
                "preploop",
                "Append entries in one transaction with a unique idempotency key. Derive the balance from the entries instead of updating it in place.",
            ),
            (
                "Design a chat inbox",
                "jordan",
                "Persist the message first, then push it through a per-user queue. An offline client catches up from the stored history.",
            ),
        ]
        solutions = {}
        for title, author, content in specs:
            solution, _ = Solution.objects.get_or_create(
                question=questions[title],
                author=users[author],
                content=content,
            )
            solutions[title] = solution
        return solutions

    def seed_comments(self, users, questions, solutions):
        rate_limit = questions["Design a rate limiter for an API"]
        parent, _ = Comment.objects.get_or_create(
            question=rate_limit,
            author=users["preploop"],
            content="Token bucket is the version I would start with.",
        )
        reply, _ = Comment.objects.get_or_create(
            reply_to=parent,
            author=users["avery"],
            content="I would still keep a sliding window for the abuse case, because a full bucket can be spent in one moment.",
        )
        shortener, _ = Comment.objects.get_or_create(
            question=questions["Design a URL shortener"],
            author=users["jordan"],
            content="Custom aliases need their own unique constraint, or they collide with generated keys.",
        )
        feed, _ = Comment.objects.get_or_create(
            question=questions["Design a news feed"],
            author=users["jordan"],
            content="Fan-out on write gets expensive for celebrity accounts. The prompt should say how large a following can be.",
        )
        solution_comment, _ = Comment.objects.get_or_create(
            solution=solutions["Design a payment ledger"],
            author=users["avery"],
            content="Rebuilding the balance from entries is clear. I would still store a checkpoint so reads do not scan the whole history.",
        )
        solution_reply, _ = Comment.objects.get_or_create(
            reply_to=solution_comment,
            author=users["preploop"],
            content="A daily checkpoint works if the checkpoint and the entries after it are read in one snapshot.",
        )
        return {
            "rate_reply": reply,
            "shortener": shortener,
            "feed": feed,
            "solution_reply": solution_reply,
        }

    def seed_reports(self, users, questions, solutions, comments):
        pending_question, _ = Report.objects.get_or_create(
            reporter=users["jordan"],
            question=questions["Design a news feed"],
            defaults={
                "reason": "The prompt never says how large a following can be, so answers cannot be compared.",
                "status": Report.Status.PENDING,
            },
        )
        pending_comment, _ = Report.objects.get_or_create(
            reporter=users["avery"],
            comment=comments["shortener"],
            defaults={
                "reason": "This comment is about a different design than the one in the prompt.",
                "status": Report.Status.PENDING,
            },
        )
        dismissed, _ = Report.objects.get_or_create(
            reporter=users["preploop"],
            solution=solutions["Design a URL shortener"],
            defaults={
                "reason": "The solution skips failure handling.",
                "status": Report.Status.DISMISSED,
                "reviewed_by": users["moderator"],
                "resolved_at": timezone.now() - timedelta(days=1),
            },
        )
        actioned, _ = Report.objects.get_or_create(
            reporter=users["avery"],
            question=questions["Draft notes on a private outage"],
            defaults={
                "reason": "The prompt includes a customer name that should not be public.",
                "status": Report.Status.ACTIONED,
                "reviewed_by": users["moderator"],
                "resolved_at": timezone.now() - timedelta(days=3),
            },
        )
        ModerationReport.objects.get_or_create(
            report=dismissed,
            defaults={
                "moderator": users["moderator"],
                "action": ModerationReport.Action.DISMISS,
                "reviewed_at": dismissed.resolved_at,
            },
        )
        ModerationReport.objects.get_or_create(
            report=actioned,
            defaults={
                "moderator": users["moderator"],
                "action": ModerationReport.Action.REMOVE,
                "reviewed_at": actioned.resolved_at,
            },
        )
        for report in (pending_question, pending_comment):
            ModerationReport.objects.get_or_create(report=report, defaults={"action": ""})
        return {
            "pending_question": pending_question,
            "pending_comment": pending_comment,
        }

    def seed_votes(self, users, questions):
        specs = [
            ("preploop", "Design a rate limiter for an API", Vote.VoteType.UPVOTE),
            ("avery", "Design a rate limiter for an API", Vote.VoteType.UPVOTE),
            ("jordan", "Design a rate limiter for an API", Vote.VoteType.DOWNVOTE),
            ("avery", "Design a news feed", Vote.VoteType.UPVOTE),
            ("jordan", "Design a URL shortener", Vote.VoteType.UPVOTE),
            ("preploop", "Design a payment ledger", Vote.VoteType.UPVOTE),
            ("moderator", "Choose indexes for an orders table", Vote.VoteType.UPVOTE),
            ("avery", "Design a distributed cache", Vote.VoteType.UPVOTE),
        ]
        for username, title, vote_type in specs:
            Vote.objects.get_or_create(
                user=users[username],
                question=questions[title],
                defaults={"vote_type": vote_type},
            )

    def seed_statuses(self, users, questions):
        specs = [
            ("preploop", "Design a URL shortener", "solved"),
            ("preploop", "Choose indexes for an orders table", "solved"),
            ("preploop", "Design a news feed", "solved"),
            ("preploop", "Design autocomplete for a product search", "solved"),
            ("preploop", "Design a chat inbox", "attempted"),
            ("preploop", "Debug a latency spike in checkout", "attempted"),
            ("avery", "Design a rate limiter for an API", "solved"),
            ("avery", "Design a distributed cache", "attempted"),
            ("jordan", "Design a payment ledger", "solved"),
            ("jordan", "Design a video upload pipeline", "attempted"),
            ("moderator", "Choose indexes for an orders table", "solved"),
        ]
        for username, title, status in specs:
            UserQuestionStatus.objects.get_or_create(
                user=users[username],
                question=questions[title],
                defaults={"status": status},
            )

    def seed_goals(self, users, companies, tags):
        deadline = (timezone.now() + timedelta(days=45)).date()
        question_count, _ = PreparationGoal.objects.get_or_create(
            user=users["preploop"],
            metric=PreparationGoal.GoalMetric.QUESTION_COUNT,
            target_tag=None,
            target_company=None,
            defaults={"target_value": 10, "deadline": deadline},
        )
        if question_count.target_value is None:
            question_count.target_value = 10
            question_count.save(update_fields=["target_value"])
        topic, _ = PreparationGoal.objects.get_or_create(
            user=users["preploop"],
            metric=PreparationGoal.GoalMetric.TOPIC_MASTERY,
            target_tag=tags["Systems"],
            defaults={"deadline": deadline},
        )
        company, _ = PreparationGoal.objects.get_or_create(
            user=users["preploop"],
            metric=PreparationGoal.GoalMetric.COMPANY_TARGET,
            target_company=companies["Google"],
            defaults={"deadline": deadline},
        )
        PreparationGoal.objects.get_or_create(
            user=users["avery"],
            metric=PreparationGoal.GoalMetric.QUESTION_COUNT,
            target_tag=None,
            target_company=None,
            defaults={"target_value": 6, "deadline": deadline},
        )
        return {"question_count": question_count, "topic": topic, "company": company}

    def seed_notifications(self, users, questions, solutions, comments, goals):
        specs = [
            (users["preploop"], Notification.NotificationType.NEW_REPLY, "comment", comments["rate_reply"].id, False),
            (users["preploop"], Notification.NotificationType.NEW_SOLUTION, "solution", solutions["Design a rate limiter for an API"].id, True),
            (users["preploop"], Notification.NotificationType.GOAL_PROGRESS, "goal", goals["question_count"].id, False),
            (users["jordan"], Notification.NotificationType.CONTENT_MODERATED, "question", questions["Draft notes on a private outage"].id, False),
            (users["moderator"], Notification.NotificationType.NEW_REPLY, "comment", comments["feed"].id, False),
            (users["avery"], Notification.NotificationType.NEW_SOLUTION, "solution", solutions["Design a payment ledger"].id, False),
        ]
        for user, kind, reference_type, reference_id, is_read in specs:
            Notification.objects.get_or_create(
                user=user,
                type=kind,
                reference_type=reference_type,
                reference_id=reference_id,
                defaults={"is_read": is_read},
            )

    def seed_tokens(self, users):
        EmailVerificationToken.objects.get_or_create(
            token="seed-verify-pending",
            defaults={
                "user": users["pending"],
                "expires_at": timezone.now() + timedelta(days=2),
            },
        )
        PasswordResetToken.objects.get_or_create(
            token="seed-reset-avery",
            defaults={
                "user": users["avery"],
                "expires_at": timezone.now() + timedelta(hours=2),
            },
        )
