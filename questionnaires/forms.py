

import uuid

from django import forms

from .models import TemplateQuestion


class TemplateQuestionAdminForm(forms.ModelForm):

    options_text = forms.CharField(
        label="گزینه‌های پاسخ",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 5}
        ),
        help_text=(
            "برای سؤال‌های انتخابی، هر گزینه را "
            "در یک خط بنویسید."
        ),
    )

    class Meta:
        model = TemplateQuestion

        fields = (
            "template",
            "text",
            "answer_type",
            "is_required",
            "order",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["options_text"].initial = "\n".join(
                option["label"]
                for option in self.instance.options
            )

    def clean(self):
        cleaned_data = super().clean()

        answer_type = cleaned_data.get("answer_type")

        if not answer_type:
            return cleaned_data

        options_text = cleaned_data.get(
            "options_text", ""
        )

        choice_types = (
            TemplateQuestion.AnswerType.SINGLE_CHOICE,
            TemplateQuestion.AnswerType.MULTIPLE_CHOICE,
        )

        if answer_type in choice_types:

            labels = [
                line.strip()
                for line in options_text.splitlines()
                if line.strip()
            ]

            if len(labels) < 2:
                self.add_error(
                    "options_text",
                    "حداقل دو گزینه وارد کنید."
                )
                return cleaned_data

            normalized_labels = [
                label.casefold()
                for label in labels
            ]

            if len(normalized_labels) != len(
                set(normalized_labels)
            ):
                self.add_error(
                    "options_text",
                    "عنوان گزینه‌ها نباید تکراری باشد."
                )
                return cleaned_data

            existing_options = {
                option["label"]: option["value"]
                for option in self.instance.options
            }

            self.instance.options = [
                {
                    "value": existing_options.get(label)
                    or uuid.uuid4().hex,
                    "label": label,
                }
                for label in labels
            ]

        else:
            if options_text.strip():
                self.add_error(
                    "options_text",
                    (
                        "برای سؤال‌های متنی، عددی یا "
                        "بله/خیر نباید گزینه وارد کنید."
                    ),
                )
            else:
                self.instance.options = []

        return cleaned_data