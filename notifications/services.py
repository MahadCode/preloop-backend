from .models import Notification


def notify(user, notification_type, reference_type, reference_id):
    if user is None:
        return None
    return Notification.objects.create(
        user=user,
        type=notification_type,
        reference_type=reference_type,
        reference_id=reference_id,
    )


def notify_goals_after_solve(user, question):
    from progress.models import PreparationGoal

    goals = PreparationGoal.objects.filter(user=user)
    for goal in goals:
        if goal.metric == PreparationGoal.GoalMetric.TOPIC_MASTERY:
            if not goal.target_tag_id or not question.tag.filter(pk=goal.target_tag_id).exists():
                continue
        elif goal.metric == PreparationGoal.GoalMetric.COMPANY_TARGET:
            if not goal.target_company_id or not question.company.filter(pk=goal.target_company_id).exists():
                continue
        notify(user, Notification.NotificationType.GOAL_PROGRESS, "goal", goal.id)
