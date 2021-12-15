FROM registry.cn-shanghai.aliyuncs.com/tcc-public/python:3
RUN pip install pandas -i https://pypi.tuna.tsinghua.edu.cn/simple
ADD . /
WORKDIR / 
CMD ["sh", "run.sh"] 
