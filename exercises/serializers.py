from rest_framework import serializers

from .models import Exercise, ExerciseMedia, MuscleGroup


class MuscleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuscleGroup
        fields = (
            "id",
            "name",
            "slug",
        )


class ExerciseMediaSerializer(serializers.ModelSerializer):
    media_type_display = serializers.CharField(
        source="get_media_type_display",
        read_only=True,
    )

    class Meta:
        model = ExerciseMedia
        fields = (
            "id",
            "media_type",
            "media_type_display",
            "file",
            "thumbnail",
            "is_primary",
            "order",
        )
        read_only_fields = fields


class ExerciseListSerializer(serializers.ModelSerializer):
    primary_muscle = MuscleGroupSerializer(
        read_only=True,
    )

    primary_media = serializers.SerializerMethodField()

    difficulty_display = serializers.CharField(
        source="get_difficulty_display",
        read_only=True,
    )

    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "primary_muscle",
            "difficulty",
            "difficulty_display",
            "is_system",
            "is_active",
            "primary_media",
        )

        read_only_fields = fields

    def get_primary_media(self, obj):
        media_items = getattr(
            obj,
            "primary_media_items",
            [],
        )

        if not media_items:
            return None

        return ExerciseMediaSerializer(
            media_items[0],
            context=self.context,
        ).data


class ExerciseDetailSerializer(serializers.ModelSerializer):
    primary_muscle = MuscleGroupSerializer(
        read_only=True,
    )

    secondary_muscles = MuscleGroupSerializer(
        many=True,
        read_only=True,
    )

    media = ExerciseMediaSerializer(
        many=True,
        read_only=True,
    )

    difficulty_display = serializers.CharField(
        source="get_difficulty_display",
        read_only=True,
    )

    copied_from_name = serializers.CharField(
        source="copied_from.name",
        read_only=True,
    )

    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "description",
            "equipment",
            "common_mistake",
            "primary_muscle",
            "secondary_muscles",
            "difficulty",
            "difficulty_display",
            "is_system",
            "is_active",
            "copied_from",
            "copied_from_name",
            "media",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class ExerciseCreateSerializer(serializers.ModelSerializer):
    media_file = serializers.FileField(
        write_only=True,
        required=False,
    )

    thumbnail = serializers.ImageField(
        write_only=True,
        required=False,
    )

    media_type = serializers.ChoiceField(
        choices=ExerciseMedia.MediaType.choices,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "description",
            "equipment",
            "common_mistake",
            "primary_muscle",
            "secondary_muscles",
            "difficulty",
            "media_file",
            "thumbnail",
            "media_type",
        )

        read_only_fields = (
            "id",
        )

    def create(self, validated_data):
        media_file = validated_data.pop(
            "media_file",
            None,
        )

        thumbnail = validated_data.pop(
            "thumbnail",
            None,
        )

        media_type = validated_data.pop(
            "media_type",
            None,
        )

        secondary_muscles = validated_data.pop(
            "secondary_muscles",
            [],
        )

        exercise = Exercise.objects.create(
            **validated_data
        )

        exercise.secondary_muscles.set(
            secondary_muscles
        )

        if media_file:
            ExerciseMedia.objects.create(
                exercise=exercise,
                media_type=(
                    media_type
                    or ExerciseMedia.MediaType.VIDEO
                ),
                file=media_file,
                thumbnail=thumbnail,
                is_primary=True,
                order=1,
            )

        return exercise


class ExerciseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = (
            "name",
            "description",
            "equipment",
            "common_mistake",
            "primary_muscle",
            "secondary_muscles",
            "difficulty",
            "is_active",
        )


class ExerciseMediaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseMedia
        fields = (
            "id",
            "media_type",
            "file",
            "thumbnail",
            "is_primary",
            "order",
        )

        read_only_fields = (
            "id",
        )

    def create(self, validated_data):
        exercise = validated_data["exercise"]

        if validated_data.get("is_primary", False):
            exercise.media.update(
                is_primary=False
            )

        return ExerciseMedia.objects.create(
            **validated_data
        )


class ExerciseMediaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseMedia
        fields = (
            "media_type",
            "file",
            "thumbnail",
            "is_primary",
            "order",
        )

        extra_kwargs = {
            "file": {
                "required": False,
            },
            "thumbnail": {
                "required": False,
            },
        }

    def update(self, instance, validated_data):
        old_file = instance.file
        old_thumbnail = instance.thumbnail
        old_file_name = old_file.name if old_file else None
        old_thumbnail_name = old_thumbnail.name if old_thumbnail else None

        file_is_replaced = "file" in validated_data
        thumbnail_is_replaced = "thumbnail" in validated_data

        is_primary = validated_data.get(
            "is_primary",
            instance.is_primary,
        )

        if is_primary:
            instance.exercise.media.exclude(
                pk=instance.pk,
            ).update(
                is_primary=False,
            )

        updated_instance = super().update(
            instance,
            validated_data,
        )

        if (
            file_is_replaced
            and old_file_name
            and old_file_name != updated_instance.file.name
        ):
            old_file.storage.delete(old_file_name)

        if (
            thumbnail_is_replaced
            and old_thumbnail_name
            and old_thumbnail_name
            != getattr(updated_instance.thumbnail, "name", None)
        ):
            old_thumbnail.storage.delete(old_thumbnail_name)

        return updated_instance
