
# MR 推送

---

## 部署

- 脚本
```shell
#bin.bash
script_dir=$(cd $(dirname $0);pwd)
echo $script_dir
git clone git@10.10.10.10:robot/test_push.git
cp test_push/python-gitlab.cfg.bk test_push/python-gitlab.cfg
vim test_push/python-gitlab.cfg
docker stop mr_01
docker rm mr_01
docker build -t mr:0.1 .
docker run -id --restart always -p 8080:8080 -v $script_dir/test_push:/data/gitlab_push --name mr_01 mr:0.1
```

- Dockerfile

```
# Version 0.1
# 基础镜像
FROM hub.test.com/devops/harbor-replicate:latest
# 维护者信息
MAINTAINER robot@test.com

RUN /app/.runtime/bin/pip install web.py -i https://mirrors.aliyun.com/pypi/simple/
RUN /app/.runtime/bin/pip install python-gitlab -i https://mirrors.aliyun.com/pypi/simple/
RUN cp /data/gitlab_push/python-gitlab.cfg /etc/python-gitlab.cfg

EXPOSE 8080

# 容器启动命令
CMD ["/app/.runtime/bin/python3", "/data/gitlab_push/receive.py"]
```
