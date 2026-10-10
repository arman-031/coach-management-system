from rest_framework import serializers

from .models import (
    NutritionDay,
    NutritionMeal,
    NutritionFoodItem
)


# ---------------------------------------
# Nutrition Day Serializer
# ---------------------------------------

class NutritionDaySerializer(serializers.ModelSerializer):

    class Meta:
        model = NutritionDay

        fields = (
            "id",
            "program",
            "title",
            "note",
            "order",
            "created_at",
        )

        read_only_fields = (
            "id",
            "program",
            "created_at",
        )

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "ترتیب روز باید حداقل ۱ باشد."
            )

        return value


# ---------------------------------------
# Nutrition Meal Serializer
# ---------------------------------------

class NutritionMealSerializer(serializers.ModelSerializer):

    class Meta:
        model = NutritionMeal

        fields = (
            "id",
            "nutrition_day",
            "title",
            "meal_time",
            "note",
            "order",
            "created_at",
        )

        read_only_fields = (
            "id",
            "nutrition_day",
            "created_at",
        )

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "عنوان وعده نمی‌تواند خالی باشد."
            )

        return value.strip()

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "ترتیب وعده باید حداقل ۱ باشد."
            )

        return value


# ---------------------------------------
# Nutrition Food Item Serializer
# ---------------------------------------

class NutritionFoodItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = NutritionFoodItem

        fields = (
            "id",
            "nutrition_meal",
            "name",
            "quantity",
            "unit",
            "note",
            "order",
            "created_at",
        )

        read_only_fields = (
            "id",
            "nutrition_meal",
            "created_at",
        )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "نام ماده غذایی نمی‌تواند خالی باشد."
            )

        return value

    def validate_order(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "ترتیب ماده غذایی باید حداقل ۱ باشد."
            )

        return value


# ---------------------------------------
# Student - Nutrition Food Item Read
# ---------------------------------------

class NutritionFoodItemReadSerializer(
    serializers.ModelSerializer
):

    unit_display = serializers.CharField(
        source="get_unit_display",
        read_only=True,
    )

    class Meta:
        model = NutritionFoodItem

        fields = (
            "id",
            "name",
            "quantity",
            "unit",
            "unit_display",
            "note",
            "order",
        )

        read_only_fields = fields


# ---------------------------------------
# Student - Nutrition Meal Read
# ---------------------------------------

class NutritionMealReadSerializer(
    serializers.ModelSerializer
):

    food_items = NutritionFoodItemReadSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = NutritionMeal

        fields = (
            "id",
            "title",
            "meal_time",
            "note",
            "order",
            "food_items",
        )

        read_only_fields = fields


# ---------------------------------------
# Student - Nutrition Day Read
# ---------------------------------------

class NutritionDayReadSerializer(
    serializers.ModelSerializer
):

    meals = NutritionMealReadSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = NutritionDay

        fields = (
            "id",
            "title",
            "note",
            "order",
            "meals",
        )

        read_only_fields = fields