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

    media = ExerciseMediaSerializer(
        many=True,
        read_only=True,
    )

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
            "media",
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