"""
4.实现yaml文件的功能：占位符函数（接口关联、时间戳、随机取值等）

yaml 里的写法统一是 ${函数名(参数)}，由 base/apiutil.py 的 replace_load 反射调用，
所以这里新增函数不用改框架代码 —— 但函数名要和 yaml 里写的一字不差。
"""
import random
import re
import time
import datetime

from common.readyaml import ReadYamlData



class DebugTalk(object):
    # 类属性：同一次运行内所有 DebugTalk 实例共享。
    # 因为 base/apiutil.py 的 replace_load 每次都是 getattr(DebugTalk(), func_name) 新建实例，
    # 用实例属性存不住，必须放在类属性上。
    _run_id = None

    def __init__(self):
        self.read = ReadYamlData()

    def get_run_id(self):
        """
        返回本次运行的唯一标识（格式 yyyyMMddHHmmss），yaml 里用 ${get_run_id()} 调用。

        用途：构造可追溯的测试数据。比如注册用户时把用户名写成 test_${get_run_id()}，
        跑完能一眼看出这条数据是哪一次自动化跑出来的，也方便清理。

        注意：同一次运行内多次调用返回同一个值（首次调用时生成），
        这样「请求参数里的取值」和「validation 里的预期值」才能对得上。
        """
        if DebugTalk._run_id is None:
            DebugTalk._run_id = time.strftime('%Y%m%d%H%M%S')
        return DebugTalk._run_id

    def get_extract_order_data(self,data,randoms):
        """
        按照排序顺序读取数据,不加0，-1，-2的情况
        """
        if randoms not in [0,-1,-2]:
            return data[randoms - 1]

    def get_extract_data(self,node_name,randoms=None):
        """
        获取extract.yaml的数据 提取返回值数据（接口关联的核心函数）

        :param node_name: extract.yaml 里的 key，例如 ${get_extract_data(token)}
        :param randoms: 取多个值时的取值方式，**不是节点名**：
                        不填   -> 原样返回（单个值，或整个列表）
                        0      -> 从列表里随机取一个
                        -1     -> 把列表拼成字符串返回（逗号分隔）
                        -2     -> 返回列表本身
                        其它数字 -> 按顺序取第 N 个，从 1 开始（1 就是第一个）
        :return:

        典型用法（testcase/Business/BusinessScenario.yml）：
            商品列表用例把 goodsId 列表提取成 goodsIds，
            后面的商品详情 / 提交订单用例写 ${get_extract_data(goodsIds,1)} 取第一个商品id。

        修复记录：
        1) 本框架原来的签名是 get_extract_data(node_name, sec_node_name=None, randoms=None)，
           第二个位置参数被当成"节点名"直接忽略掉，于是 ${get_extract_data(goodsIds,1)}
           取回来的是整个列表，商品详情接口拿到一整个数组，用例必然失败。
           现在改回原电商框架的语义：第二个位置参数就是 randoms（取值方式）。
           已确认仓库里没有别的 Python 代码用两参数形式调用它，改签名不影响其它用例。
        2) 原实现用字典字面量取值的写法（data_value = {randoms: ..., 0: random.choice(data), ...}），
           Python 会把字典里所有 value 都算一遍 —— 即使 randoms=1 也会执行 random.choice(data)
           和 ','.join(data)，取到的是空列表或非列表数据时会抛无关的异常。
           这里改成 if/elif，只执行命中的那一支。
        """
        data = self.read.get_extract_yaml(node_name)
        if randoms is None or randoms == '':
            return data
        # 占位符传进来的一定是字符串（yaml 里写 1，split(',') 之后是 '1'），
        # 用正则判断是不是数字，不是数字就按"没填"处理并提示，避免拿字符串去当索引。
        if not re.match(r'^[-+]?\d+$', str(randoms)):
            print(f'get_extract_data 的第二个参数 {randoms!r} 不是数字，已按不指定取值方式处理：'
                  f'只支持 0(随机) / -1(拼接成字符串) / -2(返回列表) / 其它数字(按顺序取第N个，从1开始)')
            return data
        randoms = int(randoms)
        if randoms == 0:
            return random.choice(data)
        if randoms == -1:
            return ','.join(data)
        if randoms == -2:
            return data
        return self.get_extract_order_data(data, randoms)

    def get_extract_data_list(self,node_name,randoms=None):
        """
        获取extract.yaml文件的数据（列表处理的老写法，保留兼容）
        :param node_name:
        :param randoms:
        :return:
        """
        data=self.read.get_extract_yaml(node_name)
        if randoms is not None:
            randoms=int(randoms)
            data_value={
                randoms : 1,
                0 : random.choice(data),
                -1 : ','.join(data),
                -2 : ','.join(data).split(',')
            }
            data=data_value[randoms]
        return data


    def Md5_params(self,params):
        """实现MD5加密"""
        return 'ABCDEFGHIJK'+str(params)

    # ------------------------------------------------------------------
    # 时间戳相关：电商的订单支付 / 订单状态查询接口都要传 timeStamp，
    # 校验订单状态接口的查询时间段也要用当天 0 点的时间戳
    # ------------------------------------------------------------------
    def timestamp(self):
        """获取当前时间戳，10位（秒级）。yaml 里写 ${timestamp()}"""
        return int(time.time())

    def timestamp_thirteen(self):
        """获取当前时间戳，13位（毫秒级）"""
        return int(time.time()) * 1000

    def today_zero_tenstamp(self):
        """获取当天00:00:00的时间戳，10位（秒级）"""
        return int(time.mktime(datetime.date.today().timetuple()))

    def today_zero_stamp(self):
        """获取当天00:00:00的时间戳，13位（毫秒级）"""
        return int(time.mktime(datetime.date.today().timetuple())) * 1000

if __name__ == '__main__':
    debugtalk = DebugTalk()
    # 演示：取 goodsIds 列表里的第一个值（等价于用例里的 ${get_extract_data(goodsIds,1)}）
    print(debugtalk.get_extract_data('goodsIds',1))
