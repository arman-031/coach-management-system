from django.urls import path

from .views import (
    StudentQuestionnaireDetailView,
    StudentQuestionnaireAnswerView,
    StudentQuestionnaireSubmitView,
    CoachQuestionnaireDetailView,
    CoachQuestionnaireRevisionView,
)


urlpatterns = [
    path(
        "my/<int:program_pk>/questionnaire/",
        StudentQuestionnaireDetailView.as_view(),
        name="student-questionnaire-detail",
    ),

    path(
        "my/<int:program_pk>/questionnaire/items/<int:item_pk>/answer/",
        StudentQuestionnaireAnswerView.as_view(),
        name="student-questionnaire-answer",
    ),

    path(
        "my/<int:program_pk>/questionnaire/submit/",
        StudentQuestionnaireSubmitView.as_view(),
        name="student-questionnaire-submit",
    ),
    path(
        "<int:program_pk>/questionnaire/",
        CoachQuestionnaireDetailView.as_view(),
        name="coach-questionnaire-detail",
    ),
    path(
        "<int:program_pk>/questionnaire/request-revision/",
        CoachQuestionnaireRevisionView.as_view(),
        name="coach-questionnaire-request-revision",
    ),
]