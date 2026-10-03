import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from exercises.models import Exercise, ExerciseMedia, MuscleGroup


class Command(BaseCommand):
    help = "وارد کردن حرکات پایه و مدیاهای آن‌ها از فایل JSON"

    def handle(self, *args, **options):
        base_path = Path(__file__).resolve().parent.parent.parent

        file_path = base_path / "data" / "exercises.json"
        media_root = base_path / "media_seed"

        with open(file_path, "r", encoding="utf-8") as file:
            exercises_data = json.load(file)

        created_count = 0
        updated_count = 0
        media_count = 0

        for item in exercises_data:
            # -------------------------
            # عضله اصلی
            # -------------------------
            primary_muscle, _ = MuscleGroup.objects.get_or_create(
                name=item["primary_muscle"],
                defaults={
                    "slug": slugify(
                        item["primary_muscle"],
                        allow_unicode=True,
                    )
                },
            )

            # -------------------------
            # خود حرکت
            # -------------------------
            exercise, created = Exercise.objects.update_or_create(
                name=item["name"],
                is_system=True,
                defaults={
                    "description": item.get("description", ""),
                    "equipment": item.get("equipment", ""),
                    "common_mistake": item.get("common_mistake", ""),
                    "primary_muscle": primary_muscle,
                    "difficulty": item.get(
                        "difficulty",
                        Exercise.Difficulty.BEGINNER,
                    ),
                    "created_by": None,
                    "is_active": True,
                },
            )

            # -------------------------
            # عضلات فرعی
            # -------------------------
            secondary_muscles = []

            for muscle_name in item.get("secondary_muscles", []):
                muscle, _ = MuscleGroup.objects.get_or_create(
                    name=muscle_name,
                    defaults={
                        "slug": slugify(
                            muscle_name,
                            allow_unicode=True,
                        )
                    },
                )

                secondary_muscles.append(muscle)

            exercise.secondary_muscles.set(secondary_muscles)

            # -------------------------
            # مدیاهای حرکت
            # -------------------------
            for media_item in item.get("media", []):
                media_path = media_root / media_item["file"]

                # اگر فایل اصلی وجود نداشت، command متوقف نشود.
                if not media_path.exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f"فایل مدیا پیدا نشد: {media_path}"
                        )
                    )
                    continue

                thumbnail_path = None

                if media_item.get("thumbnail"):
                    thumbnail_path = (
                        media_root / media_item["thumbnail"]
                    )

                # اگر command دوباره اجرا شد،
                # همان مدیا دوباره ساخته نشود.
                media_object, _ = ExerciseMedia.objects.get_or_create(
                    exercise=exercise,
                    media_type=media_item["type"],
                    order=media_item.get("order", 0),
                    defaults={
                        "is_primary": media_item.get(
                            "is_primary",
                            False,
                        ),
                    },
                )

                media_object.is_primary = media_item.get(
                    "is_primary",
                    False,
                )

                # ذخیره فایل اصلی
                with open(media_path, "rb") as media_file:
                    media_object.file.save(
                        media_path.name,
                        File(media_file),
                        save=False,
                    )

                # ذخیره thumbnail در صورت وجود
                if thumbnail_path and thumbnail_path.exists():
                    with open(
                        thumbnail_path,
                        "rb",
                    ) as thumbnail_file:
                        media_object.thumbnail.save(
                            thumbnail_path.name,
                            File(thumbnail_file),
                            save=False,
                        )

                media_object.save()
                media_count += 1

            # -------------------------
            # شمارش نتیجه
            # -------------------------
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{created_count} حرکت ساخته شد، "
                f"{updated_count} حرکت بروزرسانی شد و "
                f"{media_count} مدیا پردازش شد."
            )
        )