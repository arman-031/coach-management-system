from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "COACH")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("کاربر مدیر باید is_staff=True داشته باشد.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("کاربر مدیر باید is_superuser=True داشته باشد.")

        return self.create_user(phone, password, **extra_fields)