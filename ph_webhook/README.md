部署说明：
将代码clone在路径/data/message_service，将/data/message_service/ph_webhook/ph_webhook/setting_example.py 复制一份并改名为 setting.py，更改相关配置，特别是数据库部分

测试服务：
可以在/data/message_service/ph_webhook目录下运行 python3 manage.py runserver 0:5000 看服务能否起来。

运行镜像：
docker run -p 5000:5000 --restart always --name ph_webhook1.0.0 \
-v /data/message_service/ph_webhook:/backend \
-d art-internal.test.com/scm-docker/ph_webhook:1.0.0

镜像制作：
dockerfile在 docker_env路径，当前版本 ph_webhook1.0.0

服务升级：
将/data/message_service/ph_webhook中的代码pull到最新或者更改相应配置，然后重启docker即可。