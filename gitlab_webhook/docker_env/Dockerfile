FROM hub.test.com/builder/python38-base-backend:latest
WORKDIR /backend
RUN python3 -m pip install -i https://art-internal.test.com/artifactory/api/pypi/pypi/simple uwsgi \
    && python3 -m pip install -i https://art-internal.test.com/artifactory/api/pypi/pypi/simple python-gitlab
#用uwsgi运行django项目（这里运行的进程不要以后台运行比如nohup，uwsgi -d等）
#为什么不要用后台方式运行？   因为后台运行方式启动，容器会认为服务没起来，从而导致容器停止
#注释掉uwsgi.ini里的daemonize ,不然docker秒退。
ENTRYPOINT ["uwsgi"]
CMD ["--ini", "uwsgi.ini"] 

