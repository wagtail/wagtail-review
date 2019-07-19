# Generated by Django 2.2.3 on 2019-07-17 13:45

from django.db import migrations


def reviewer_to_user(models, reviewer):
    if reviewer.user:
        user, created = models.User.objects.get_or_create(
            internal=reviewer.user,
        )
        return user
    else:
        external_user, created = models.ExternalUser.objects.get_or_create(
            email=reviewer.email,
        )
        share, created = models.Share.objects.get_or_create(
            external_user=external_user,
            page_id=reviewer.review.page_revision.page_id,
            defaults={
                'shared_by_id': reviewer.review.submitter_id,
                'shared_at': reviewer.review.created_at,
                'can_comment': True,
            }
        )
        user, created = models.User.objects.get_or_create(
            external=external_user,
        )
        return user


def review_to_review_request(models, review):
    request = models.ReviewRequest.objects.create(
        page_revision_id=review.page_revision_id,
        submitted_by_id=review.submitter_id,
        submitted_at=review.created_at,
    )

    # Reviewers
    request.assignees.set([
        reviewer_to_user(models, reviewer)
        for reviewer in review.reviewers.all()
    ])

    # Annotations
    for annotation in models.Annotation.objects.filter(reviewer__review=review).select_related('reviewer'):
        annotation_range = annotation.ranges.first()

        models.Comment.create(
            page_revision_id=review.page_revision_id,
            user=reviewer_to_user(models, annotation.reviewer),
            quote=annotation.quote,
            text=annotation.text,
            created_at=annotation.created_at,
            updated_at=annotation.updated_at,
            resolved_at=annotation.created_at if review.status == 'closed' else None,
            content_path='!unknown',
            start_xpath=annotation_range.start,
            start_offset=annotation_range.start_offset,
            end_xpath=annotation_range.end,
            end_offset=annotation_range.end_offset,
        )

    # Responses
    for response in models.Response.objects.filter(reviewer__review=review).select_related('reviewer'):
        models.ReviewResponse.objects.create(
            request=request,
            submitted_by=reviewer_to_user(models, response.reviewer),
            submitted_at=response.created_at,
            status=models.ReviewResponse.STATUS_APPROVED if response.result == 'approve' else models.ReviewResponse.STATUS_NEEDS_CHANGES,
            comment=response.comment,
        )

    return request


class Models:
    def __init__(self, apps):
        self.ExternalUser = apps.get_model('wagtail_review.ExternalUser')
        self.Share = apps.get_model('wagtail_review.Share')
        self.User = apps.get_model('wagtail_review.User')
        self.Comment = apps.get_model('wagtail_review.Comment')
        self.ReviewRequest = apps.get_model('wagtail_review.ReviewRequest')
        self.ReviewResponse = apps.get_model('wagtail_review.ReviewResponse')

        self.Review = apps.get_model('wagtail_review.Review')
        self.Annotation = apps.get_model('wagtail_review.Annotation')
        self.Response = apps.get_model('wagtail_review.Response')


def migrate_into_new_models(apps, schema_editor):
    models = Models(apps)

    for review in models.Review.objects.all().iterator():
        review_request = review_to_review_request(models, review)


class Migration(migrations.Migration):

    dependencies = [
        ('wagtail_review', '0005_reviewrequest_reviewresponse'),
    ]

    operations = [
        migrations.RunPython(migrate_into_new_models),
    ]
