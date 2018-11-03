from sqlalchemy import create_engine
import sqlalchemy
from pprint import pprint
from pymongo import MongoClient


# get fields
def get_fields(engine, tablename):
    md = sqlalchemy.MetaData()
    table = sqlalchemy.Table(tablename, md, autoload=True, autoload_with=engine)
    columns = table.c
    return columns.keys()


# 数据转移：mysql -> MongoDB
def data_migration(engine_mysql, engine_mongo, tablename):
    # 获取原始数据字段名称
    tableField = get_fields(engine_mysql, tablename)
    # print(carTableField)
    rs = engine_mysql.execute('select * from %s' % tablename)
    datas = rs.fetchall()
    for data in datas:
        newdata = dict(zip(tableField, data))
        # setattr(engine_mongo, tablename, None)
        # getattr(engine_mongo, tablename).insert_one(newdata)
        if tablename == 'carinfo':
            engine_mongo.carinfo.insert_one(newdata)
        elif tablename == 'driverinfo':
            engine_mongo.driverinfo.insert_one(newdata)


if __name__ == '__main__':
    # 连接mysql数据库
    password = input('请输入数据库密码：')
    sqlStr = 'mysql+pymysql://nds:' + password + '@192.168.1.104/ndsdata'
    engine_mysql = create_engine(sqlStr)
    conn_mysql = engine_mysql.connect()

    # 连接MongoDB数据库
    mongoClient = MongoClient('mongodb://localhost')
    mongodb = mongoClient.ndsdata

    # 转移
    # data_migration(engine_mysql=engine_mysql, engine_mongo=mongodb, tablename='carinfo')
    # data_migration(engine_mysql=engine_mysql, engine_mongo=mongodb, tablename='driverinfo')

