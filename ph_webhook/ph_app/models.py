from django.db import models


# Create your models here.


class PhUser(models.Model):
    id = models.AutoField(primary_key=True)  # 该字段可以不写，它会自动补全
    ph_id = models.CharField(max_length=255, unique=True)
    user_name = models.CharField(max_length=255, unique=True)

    def __str__(self):  # 重写直接输出类的方法
        return "%s %s" % (self.ph_id, self.user_name)

    class Meta:
        verbose_name_plural = 'PH用户列表'
        verbose_name = 'PH用户'
